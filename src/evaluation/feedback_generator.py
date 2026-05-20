"""L4 Feedback Generator: LLM-based natural language feedback for assessments."""
import logging
from typing import Optional

from src.evaluation.models import (
    L4Assessment, L4Rule, RuleMatchDetail, Grade, SuggestionType,
)
from src.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


class FeedbackGenerator:
    """Generates natural language feedback and suggestions for L4 assessments.

    Uses an LLM to produce detailed, actionable feedback based on
    assessment results and rule match details.
    """

    SYSTEM_PROMPT = (
        "你是一个电池拆卸方案评估专家。根据评估结果，生成简洁、专业的中文反馈意见。"
        "反馈应包含：整体评价、具体改进建议、风险提示。"
        "语言风格：专业、简洁、可操作。"
    )

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client

    def generate(
        self,
        assessment: L4Assessment,
        active_rules: list[L4Rule],
    ) -> dict:
        """Generate structured feedback for an assessment.

        Args:
            assessment: The L4 assessment result.
            active_rules: All active rules used in evaluation.

        Returns:
            Dict with "summary", "suggestions", "risks", and "raw_feedback" keys.
        """
        matched = [m for m in assessment.rule_matches if m.matched]
        unmatched = [m for m in assessment.rule_matches if not m.matched]

        rule_lookup = {r.rule_id: r for r in active_rules}

        summary = self._build_summary(assessment, matched, unmatched)
        suggestions = self._build_suggestions(unmatched, rule_lookup)
        risks = self._build_risks(assessment, unmatched, rule_lookup)

        result = {
            "summary": summary,
            "suggestions": suggestions,
            "risks": risks,
            "raw_feedback": assessment.feedback_text,
        }

        # Enhance with LLM if available
        if self.llm:
            try:
                llm_feedback = self._generate_llm_feedback(assessment, matched, unmatched, rule_lookup)
                result["llm_feedback"] = llm_feedback
            except Exception as e:
                logger.warning(f"LLM feedback generation failed: {e}")
                result["llm_feedback"] = None

        return result

    def _build_summary(
        self,
        assessment: L4Assessment,
        matched: list[RuleMatchDetail],
        unmatched: list[RuleMatchDetail],
    ) -> str:
        grade_label = {"高": "优秀", "中": "合格", "低": "需改进"}
        label = grade_label.get(assessment.overall_grade.value, assessment.overall_grade.value)

        total = len(assessment.rule_matches)
        return (
            f"方案整体评价：{label}（得分 {assessment.overall_score:.2f}）。"
            f"共 {total} 条规则，{len(matched)} 条匹配，{len(unmatched)} 条未匹配。"
        )

    def _build_suggestions(
        self,
        unmatched: list[RuleMatchDetail],
        rule_lookup: dict[str, L4Rule],
    ) -> list[dict]:
        suggestions = []
        for m in unmatched:
            rule = rule_lookup.get(m.rule_id)
            if not rule:
                continue

            suggestion = {
                "rule_id": m.rule_id,
                "rule_name": m.rule_name,
                "type": SuggestionType.IMPROVEMENT.value,
                "message": f"建议改进：{m.reason}",
                "conditions": [],
            }

            if rule:
                for cond in rule.conditions:
                    suggestion["conditions"].append({
                        "condition_type": cond.condition_type,
                        "target_label": cond.target_label,
                    })

            suggestions.append(suggestion)

        return suggestions

    def _build_risks(
        self,
        assessment: L4Assessment,
        unmatched: list[RuleMatchDetail],
        rule_lookup: dict[str, L4Rule],
    ) -> list[dict]:
        risks = []

        if assessment.overall_grade == Grade.LOW:
            risks.append({
                "level": "high",
                "message": "方案整体可拆卸性较低，建议全面审查设计方案。",
            })

        for m in unmatched:
            rule = rule_lookup.get(m.rule_id)
            if rule and rule.conclusion_grade == Grade.HIGH:
                risks.append({
                    "level": "medium",
                    "message": f"高权重规则 '{m.rule_name}' 未匹配，可能影响拆卸效率。",
                    "rule_id": m.rule_id,
                })

        return risks

    def _generate_llm_feedback(
        self,
        assessment: L4Assessment,
        matched: list[RuleMatchDetail],
        unmatched: list[RuleMatchDetail],
        rule_lookup: dict[str, L4Rule],
    ) -> str:
        """Use LLM to generate detailed natural language feedback."""
        matched_text = "\n".join(
            f"  - {m.rule_name}: 贡献 {m.score_contribution:.2f}"
            for m in matched
        ) or "  无"

        unmatched_details = []
        for m in unmatched:
            rule = rule_lookup.get(m.rule_id)
            if rule:
                conds = ", ".join(
                    f"{c.condition_type}({c.target_label})" for c in rule.conditions
                )
                unmatched_details.append(f"  - {m.rule_name}: 条件=[{conds}]")
            else:
                unmatched_details.append(f"  - {m.rule_name}")
        unmatched_text = "\n".join(unmatched_details) or "  无"

        prompt = f"""根据以下评估结果，生成改进建议：

整体得分：{assessment.overall_score:.2f}
整体等级：{assessment.overall_grade.value}

已匹配规则：
{matched_text}

未匹配规则：
{unmatched_text}

请提供：
1. 总体评价（2-3句话）
2. 具体改进建议（针对每个未匹配规则）
3. 风险提示（如适用）

请用中文回答，保持简洁专业。"""

        response = self.llm.generate(prompt, system_message=self.SYSTEM_PROMPT)
        return response
