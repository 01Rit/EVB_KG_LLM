"""FuzzyScorer: LLM-based fuzzy condition scoring with caching."""
import logging
import re
from typing import Optional

from src.evaluation.models import Dimension, L4Rule, L4RuleCondition

logger = logging.getLogger(__name__)

FUZZY_PROMPT_TEMPLATE = """你是动力电池拆卸领域专家。请评估以下设计实体满足规则条件的程度。

## 规则信息
- 规则名称: {rule_name}
- 规则描述: {rule_description}
- 所属维度: {dimension}
- 规则结论: 匹配时评分 {conclusion_score}，等级 {conclusion_grade}

## 待评估条件
- 条件类型: {condition_type}（{condition_type_desc}）
- 条件要求: {target_label}

## 设计中的实际信息
- 实体名称: {actual_name}
- 实体类型: {actual_labels}
- 关系信息: {actual_rel_info}

## 评分标准
{dimension_guidance}

评分等级:
- 1.0: 完全满足（本质相同，如"高强度螺栓"对"螺栓连接"）
- 0.7~0.9: 高度满足（功能等价，如"内六角螺栓"对"外六角螺栓"）
- 0.4~0.6: 部分满足（有相关性但有明显差异，如"卡扣连接"对"螺栓连接"）
- 0.1~0.3: 勉强满足（仅有微弱关联，如"焊接"对"螺栓"）
- 0.0: 完全不满足（无关联）

只返回 0~1 的数字，不要解释:"""

CONDITION_TYPE_DESC = {
    "REQUIRES_CONNECTION": "需要特定连接方式",
    "REQUIRES_TOOL": "需要特定工具",
    "REQUIRES_STRUCTURE": "需要特定结构特征",
    "CONSTRAINED_BY": "受特定因素约束",
}

DIMENSION_GUIDANCE = {
    Dimension.TECHNICAL: "技术维度重点评估：连接方式的可拆卸性相似度、工具的通用性和替代可能性、结构特征的功能等价性",
    Dimension.ECONOMIC: "经济维度重点评估：成本影响的同向性（都是增加/降低成本）、时间和人力需求的可比性",
    Dimension.ENVIRONMENTAL: "环境维度重点评估：废料/污染影响的同向性、资源利用率的可比性",
}


class FuzzyScorer:
    def __init__(self, llm_client):
        self.llm = llm_client
        self._cache: dict[tuple, float] = {}

    def score(
        self,
        condition_type: str,
        target_label: str,
        actual_name: str,
        actual_labels: str = "",
        actual_rel_info: str = "",
        rule_name: str = "",
        rule_description: str = "",
        dimension: Dimension = Dimension.TECHNICAL,
        conclusion_score: float = 0.5,
        conclusion_grade: str = "合格",
    ) -> float:
        cache_key = (condition_type, target_label, actual_name)
        if cache_key in self._cache:
            return self._cache[cache_key]

        if target_label == actual_name:
            self._cache[cache_key] = 1.0
            return 1.0

        prompt = FUZZY_PROMPT_TEMPLATE.format(
            rule_name=rule_name,
            rule_description=rule_description,
            dimension=dimension.value,
            conclusion_score=conclusion_score,
            conclusion_grade=conclusion_grade,
            condition_type=condition_type,
            condition_type_desc=CONDITION_TYPE_DESC.get(condition_type, ""),
            target_label=target_label,
            actual_name=actual_name,
            actual_labels=actual_labels,
            actual_rel_info=actual_rel_info,
            dimension_guidance=DIMENSION_GUIDANCE.get(dimension, ""),
        )

        try:
            response = self.llm.generate(prompt)
            score = self._parse_score(response)
            self._cache[cache_key] = score
            return score
        except Exception as e:
            logger.warning(f"Fuzzy scoring failed: {e}")
            return 0.0

    def _parse_score(self, response: str) -> float:
        match = re.search(r'(-?\d*\.?\d+)', response.strip())
        if not match:
            return 0.0
        value = float(match.group(1))
        return max(0.0, min(1.0, value))

    def clear_cache(self):
        self._cache.clear()
