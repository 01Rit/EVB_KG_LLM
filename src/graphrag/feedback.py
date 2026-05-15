from typing import List, Dict, Any

from src.graphrag.retriever import MultiPathRetriever
from src.graphrag.ranker import EvidenceRanker
from src.graphrag.generator import PlanGenerator
from src.graphrag.reasoning_trace import ReasoningTrace
from src.graphrag.depth_evaluator import DepthEvaluator
from src.graphrag.structured_reasoning import ConfidenceResult
from src.kg.models import EvidenceGraph, EvidenceNode
from src.utils.llm_client import LLMClient
import logging

logger = logging.getLogger(__name__)


class FeedbackLoop:
    def __init__(
        self,
        retriever: MultiPathRetriever,
        ranker: EvidenceRanker,
        generator: PlanGenerator,
        llm_client: LLMClient,
        max_iterations: int = 3,
    ):
        self.retriever = retriever
        self.ranker = ranker
        self.generator = generator
        self.max_iterations = max_iterations
        self.depth_evaluator = DepthEvaluator(llm_client)

    async def refine(
        self,
        query: str,
        initial_plan: dict,
        evidence: EvidenceGraph,
        battery_model: str,
        intents: List[str],
    ) -> tuple[dict, EvidenceGraph, List[ReasoningTrace]]:
        """
        反馈迭代优化。

        Returns:
            (refined_plan, enriched_evidence, reasoning_traces)
        """
        traces: List[ReasoningTrace] = []
        current_plan = initial_plan

        for iteration in range(self.max_iterations):
            trace = ReasoningTrace(query=query, iteration=iteration)
            logger.info(f"Feedback iteration {iteration + 1}")

            # 1. 动态深度评估
            depth = await self.depth_evaluator.evaluate(evidence, intents, query)
            trace.target_depth = depth

            # 2. 提取缺失证据
            missing_evidence = self._extract_missing_evidence(current_plan, evidence)
            trace.missing_evidence = missing_evidence

            if not missing_evidence:
                logger.info(f"No missing evidence, stopping at iteration {iteration + 1}")
                break

            # 3. 按深度进行跨层检索
            nodes = await self._retrieve_cross_layer(missing_evidence, trace, depth)
            evidence.expand(nodes)

            # 4. 置信度因子计算
            factors = self._calc_confidence_factors(evidence, current_plan)
            trace.confidence_factors = factors
            confidence_result = ConfidenceResult.compute(factors)
            trace.confidence = confidence_result.overall
            trace.confidence_result = confidence_result.model_dump()

            # 5. 记录推理步骤
            trace.reasoning_steps.append(
                f"迭代 {iteration + 1}: depth={depth}, "
                f"检索节点 {len(nodes)} (L1={len(trace.cross_layer_expansion.get('l1_nodes', []))}, "
                f"L2={len(trace.cross_layer_expansion.get('l2_nodes', []))}, "
                f"L3={len(trace.cross_layer_expansion.get('l3_nodes', []))}), "
                f"置信度 {confidence_result.overall:.2f} ({confidence_result.grade})"
            )

            traces.append(trace)

            # 6. 再生成
            current_plan = self.generator.regenerate(query, evidence, battery_model)

        return current_plan, evidence, traces

    def _extract_missing_evidence(self, plan: dict, evidence: EvidenceGraph) -> list[str]:
        """提取 plan 中 evidence 不足的步骤"""
        missing = []
        plan_steps = plan.get("steps", [])
        evidence_ids = {node.id for node in evidence.nodes}

        for step in plan_steps:
            step_evidence = step.get("evidence", [])
            if not step_evidence or all(e not in evidence_ids for e in step_evidence):
                component = step.get("component", "")
                if component:
                    missing.append(component)

        return missing[:10]

    async def _retrieve_cross_layer(
        self, missing_items: list, trace: ReasoningTrace, depth: int
    ) -> list:
        """按动态深度进行跨层检索"""
        all_nodes = []

        for item in missing_items:
            # L1: Component
            l1_nodes = self.retriever._retrieve_components(item, top_k=5)
            trace.cross_layer_expansion.setdefault("l1_nodes", []).extend(l1_nodes)
            all_nodes.extend(l1_nodes)

            if depth >= 1:
                # L1→L2: REFERENCE_OF
                l2_nodes = self._get_l2_nodes([n.id for n in l1_nodes if hasattr(n, "id")])
                trace.cross_layer_expansion.setdefault("l2_nodes", []).extend(l2_nodes)
                all_nodes.extend(l2_nodes)

                if depth >= 2:
                    # L2→L3: DEFINITION_OF
                    l3_nodes = self._get_l3_nodes([n.id for n in l2_nodes if hasattr(n, "id")])
                    trace.cross_layer_expansion.setdefault("l3_nodes", []).extend(l3_nodes)
                    all_nodes.extend(l3_nodes)

        trace.retrieved_nodes.extend(all_nodes)
        return all_nodes

    def _get_l2_nodes(self, l1_ids: list) -> list:
        """通过Neo4j查询L1→L2的REFERENCE_OF关系"""
        if not l1_ids:
            return []

        query = """
        MATCH (c:Component)-[r:REFERENCE_OF]->(e:L2_Entity)
        WHERE c.id IN $l1_ids
        RETURN e.id as id, e.name as name, e.entity_type as entity_type,
               e.battery_model as battery_model, e.source_evidence as source_evidence
        LIMIT 50
        """
        try:
            results = self.retriever.neo4j.execute_query(query, {"l1_ids": l1_ids})
            nodes = []
            for r in results:
                nodes.append(EvidenceNode(
                    node_type='L2_Entity',
                    id=r.get('id', ''),
                    name=r.get('name', ''),
                    properties=r,
                    text=f"Entity: {r.get('name')}, Type: {r.get('entity_type')}, Evidence: {r.get('source_evidence', '')}"
                ))
            return nodes
        except Exception as e:
            logger.error(f"_get_l2_nodes failed: {e}")
            return []

    def _get_l3_nodes(self, l2_ids: list) -> list:
        """通过Neo4j查询L2→L3的DEFINITION_OF关系"""
        if not l2_ids:
            return []

        query = """
        MATCH (e:L2_Entity)-[r:DEFINITION_OF]->(t:L3_Term)
        WHERE e.id IN $l2_ids
        RETURN t.id as id, t.name as name, t.definition as definition,
               t.source_evidence as source_evidence
        LIMIT 50
        """
        try:
            results = self.retriever.neo4j.execute_query(query, {"l2_ids": l2_ids})
            nodes = []
            for r in results:
                nodes.append(EvidenceNode(
                    node_type='L3_Term',
                    id=r.get('id', ''),
                    name=r.get('name', ''),
                    properties=r,
                    text=f"Term: {r.get('name')}, Definition: {r.get('definition', '')}"
                ))
            return nodes
        except Exception as e:
            logger.error(f"_get_l3_nodes failed: {e}")
            return []

    def _calc_confidence_factors(self, evidence: EvidenceGraph, plan: dict) -> dict:
        """计算置信度三因子"""
        # evidence_coverage: 有 evidence 支撑的步骤 / 总步骤数
        plan_steps = plan.get("steps", [])
        if not plan_steps:
            return {"evidence_coverage": 0.0, "cross_layer_depth": 0.0, "consistency": 0.5}

        evidence_ids = {node.id for node in evidence.nodes}
        covered_steps = 0
        for step in plan_steps:
            step_ev = step.get("evidence", [])
            if step_ev and any(e in evidence_ids for e in step_ev):
                covered_steps += 1
        evidence_coverage = covered_steps / len(plan_steps)

        # cross_layer_depth: 各步骤最高层归一化平均 (L1=0.33, L2=0.67, L3=1.0)
        # 从 evidence 节点的层分布估算
        l1_nodes = [n for n in evidence.nodes if n.node_type in ("Component", "L1_Component")]
        l2_nodes = [n for n in evidence.nodes if n.node_type in ("L2_Entity", "L2_Document", "Document", "Entity")]
        l3_nodes = [n for n in evidence.nodes if n.node_type in ("L3_Term", "Term")]
        l1_count = len(l1_nodes)
        l2_count = len(l2_nodes)
        l3_count = len(l3_nodes)
        total = l1_count + l2_count + l3_count
        if total > 0:
            cross_layer_depth = (l1_count * 0.33 + l2_count * 0.67 + l3_count * 1.0) / total
        else:
            cross_layer_depth = 0.0

        # consistency: 步骤依赖一致性（简化版：检查 evidence 图谱是否有矛盾）
        # 简化：consistency = 1.0 - (矛盾步骤数 / 总步骤数)
        # 此处用 LLM 评估成本高，先用固定值，待后续优化
        consistency = 0.75

        return {
            "evidence_coverage": evidence_coverage,
            "cross_layer_depth": cross_layer_depth,
            "consistency": consistency,
        }
