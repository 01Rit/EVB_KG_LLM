import structlog
import hashlib
from typing import List, Dict, Any

from src.kg.models import EvidenceGraph
from src.utils.llm_client import LLMClient

logger = structlog.get_logger()


class DepthEvaluator:
    """
    动态深度评估器 — 混合路径C（静态初筛 + LLM仲裁）

    深度等级：
        0 = L1 only（证据充足）
        1 = L1→L2（需要扩展）
        2 = L1→L2→L3（全链路）

    初始阈值待快速10条标注后调优。
    """

    def __init__(
        self,
        llm_client: LLMClient,
        coverage_high: float = 0.65,
        coverage_low: float = 0.10,
    ):
        self.llm = llm_client
        self.coverage_high = coverage_high
        self.coverage_low = coverage_low
        self.logger = logger

    async def evaluate(
        self,
        evidence: EvidenceGraph,
        intents: List[str],
        query: str = "",
    ) -> int:
        """评估需要的跨层检索深度"""
        # 根据 node_type 过滤各层节点
        l1_nodes = [n for n in evidence.nodes if n.node_type in ("Component", "L1_Component")]
        l2_nodes = [n for n in evidence.nodes if n.node_type in ("L2_Entity", "L2_Document", "Document", "Entity")]
        l3_nodes = [n for n in evidence.nodes if n.node_type in ("L3_Term", "Term")]

        l1_count = len(l1_nodes)
        l2_count = len(l2_nodes)
        l3_count = len(l3_nodes)

        l1_coverage = self._calc_intent_coverage(l1_nodes, intents)
        l2_coverage = self._calc_intent_coverage(l2_nodes, intents)
        l3_coverage = self._calc_intent_coverage(l3_nodes, intents)

        # 静态初筛（不走LLM）
        depth = self._static_evaluate(l1_coverage, l1_count)
        llm_arb = self._in_gray_zone(l1_coverage)

        # 写日志（用于后续调优）
        self.logger.info(
            "depth_evaluation",
            query_hash=hashlib.md5(query.encode()).hexdigest()[:8],
            l1_coverage=round(l1_coverage, 3),
            l2_coverage=round(l2_coverage, 3),
            l3_coverage=round(l3_coverage, 3),
            l1_count=l1_count,
            l2_count=l2_count,
            l3_count=l3_count,
            static_depth=depth,
            llm_arbitrated=llm_arb,
            final_depth=depth,
            battery_model=getattr(evidence, "battery_model", None),
        )

        # 灰色地带：LLM仲裁
        if llm_arb:
            depth = await self._llm_arbitrate(
                l1_count=l1_count,
                l2_count=l2_count,
                l3_count=l3_count,
                l1_coverage=l1_coverage,
            )

        return depth

    def _static_evaluate(self, l1_coverage: float, l1_count: int) -> int:
        """静态深度评估（不走LLM）"""
        if l1_coverage >= self.coverage_high and l1_count >= 10:
            return 0  # 明确充足
        if l1_coverage <= self.coverage_low:
            return 2  # 明确不足 → 全链路
        return 1  # 灰色地带

    def _in_gray_zone(self, l1_coverage: float) -> bool:
        """是否在灰色地带（需要LLM仲裁）"""
        return self.coverage_low < l1_coverage < self.coverage_high

    async def _llm_arbitrate(
        self,
        l1_count: int,
        l2_count: int,
        l3_count: int,
        l1_coverage: float,
    ) -> int:
        """LLM仲裁深度"""
        prompt = (
            f"分析以下证据覆盖情况：\n"
            f"- L1节点：{l1_count}个，L1覆盖率：{l1_coverage:.2f}\n"
            f"- L2节点：{l2_count}个\n"
            f"- L3节点：{l3_count}个\n"
            f"判断需要哪种深度的跨层检索？\n"
            f"0 = L1证据充足，不需要跨层\n"
            f"1 = 需要L1→L2扩展\n"
            f"2 = 需要L1→L2→L3全链路\n"
            f"只返回数字0、1或2，不要解释。"
        )
        try:
            result = self.llm.generate(prompt).strip()
            return int(result) if result in ["0", "1", "2"] else 1
        except Exception:
            return 1  # 出错默认L1→L2

    def _calc_intent_coverage(
        self, nodes: List[Any], intents: List[str]
    ) -> float:
        """计算节点对意图的覆盖率"""
        if not intents or not nodes:
            return 0.0

        covered = set()
        all_terms = set()
        for intent in intents:
            all_terms.update(self._tokenize(intent))

        for node in nodes:
            node_text = getattr(node, "name", "") or ""
            node_text += " " + (getattr(node, "text", "") or "")
            node_text += " " + " ".join(
                str(v) for v in getattr(node, "properties", {}).values() if v
            )
            node_terms = self._tokenize(node_text)
            if node_terms & all_terms:
                covered.update(node_terms & all_terms)

        return len(covered) / len(all_terms) if all_terms else 0.0

    def _tokenize(self, text: str) -> set:
        """简单分词"""
        import re
        text_lower = text.lower()
        tokens = re.findall(r"[\w]+", text_lower)
        stopwords = {"的", "是", "在", "了", "和", "与", "或", "及", "等", "the", "a", "an", "and", "or", "is", "in"}
        return {t for t in tokens if t not in stopwords and len(t) > 1}
