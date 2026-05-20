"""L4 Evaluation Engine: weighted scoring and reasoning path generation."""
import logging
import uuid
from typing import Optional

from src.evaluation.models import (
    L4Rule, L4Assessment, RuleMatchDetail, ReasoningPath, Grade,
    AssessmentStatus, RuleStatus,
)
from src.evaluation.rule_engine import RuleEngine

logger = logging.getLogger(__name__)


class Evaluator:
    """Evaluates design subgraphs against L4 rules, producing assessments
    with weighted scores and reasoning paths."""

    def __init__(self, rule_engine: RuleEngine):
        self.rule_engine = rule_engine

    def evaluate(self, version_id: str, subgraph: dict) -> L4Assessment:
        """Evaluate a design subgraph against all active rules.

        Args:
            version_id: The design version being evaluated.
            subgraph: Dict with "nodes" and "relationships" representing the design.

        Returns:
            L4Assessment with overall score, grade, rule matches, and feedback.
        """
        active_rules = self.rule_engine.get_rules(status=RuleStatus.ACTIVE)
        if not active_rules:
            logger.warning("No active rules found for evaluation")
            return self._empty_assessment(version_id)

        rule_matches: list[RuleMatchDetail] = []
        matched_rule_ids: list[str] = []
        unmatched_rules: list[dict] = []
        total_weighted_score = 0.0
        total_weight = 0.0

        for rule in active_rules:
            matched, details = self.rule_engine.match_rule(rule, subgraph)
            contribution = rule.conclusion_score * rule.weight if matched else 0.0

            match_detail = RuleMatchDetail(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                matched=matched,
                score_contribution=contribution,
                matched_pattern=self._format_pattern(details),
                reason=self._format_reason(rule, matched, details),
            )
            rule_matches.append(match_detail)

            if matched:
                matched_rule_ids.append(rule.rule_id)
                total_weighted_score += rule.conclusion_score * rule.weight
            else:
                unmatched_rules.append({
                    "rule_id": rule.rule_id,
                    "rule_name": rule.name,
                    "conditions": [
                        {
                            "condition_type": d["condition_type"],
                            "target_label": d["target_label"],
                            "matched": d["matched"],
                        }
                        for d in details
                    ],
                })

            total_weight += rule.weight

        overall_score = total_weighted_score / total_weight if total_weight > 0 else 0.0
        overall_grade = self._score_to_grade(overall_score)

        reasoning_path = ReasoningPath(
            path_id=f"path_{uuid.uuid4().hex[:8]}",
            assessment_id="",  # will be set after assessment is created
            matched_rule_ids=matched_rule_ids,
            evaluation_chain=rule_matches,
            aggregate_score=overall_score,
            unmatched_rules=unmatched_rules,
            confidence_factors=self._compute_confidence(rule_matches, total_weight),
        )

        feedback = self._generate_feedback(overall_score, overall_grade, rule_matches)

        assessment = L4Assessment(
            assessment_id=f"assess_{uuid.uuid4().hex[:8]}",
            version_id=version_id,
            overall_score=round(overall_score, 4),
            overall_grade=overall_grade,
            rule_matches=rule_matches,
            feedback_text=feedback,
            status=AssessmentStatus.PENDING_REVIEW,
        )

        # Backfill assessment_id into reasoning path
        reasoning_path.assessment_id = assessment.assessment_id

        logger.info(
            f"Evaluation complete for {version_id}: "
            f"score={overall_score:.4f}, grade={overall_grade.value}, "
            f"matched={len(matched_rule_ids)}/{len(active_rules)} rules"
        )

        return assessment

    def _empty_assessment(self, version_id: str) -> L4Assessment:
        return L4Assessment(
            assessment_id=f"assess_{uuid.uuid4().hex[:8]}",
            version_id=version_id,
            overall_score=0.0,
            overall_grade=Grade.LOW,
            rule_matches=[],
            feedback_text="No active rules available for evaluation.",
            status=AssessmentStatus.PENDING_REVIEW,
        )

    def _score_to_grade(self, score: float) -> Grade:
        if score >= 0.7:
            return Grade.HIGH
        elif score >= 0.4:
            return Grade.MEDIUM
        return Grade.LOW

    def _format_pattern(self, details: list[dict]) -> str:
        parts = []
        for d in details:
            status = "OK" if d["matched"] else "MISS"
            parts.append(f"{d['condition_type']}({d['target_label']})={status}")
        return "; ".join(parts)

    def _format_reason(self, rule: L4Rule, matched: bool, details: list[dict]) -> str:
        if matched:
            return f"Rule '{rule.name}' fully matched ({len(details)} conditions)"
        failed = [d for d in details if not d["matched"]]
        targets = ", ".join(d["target_label"] for d in failed)
        return f"Rule '{rule.name}' failed on: {targets}"

    def _compute_confidence(self, rule_matches: list[RuleMatchDetail], total_weight: float) -> dict:
        matched = [r for r in rule_matches if r.matched]
        unmatched = [r for r in rule_matches if not r.matched]
        coverage = len(matched) / len(rule_matches) if rule_matches else 0.0
        return {
            "rule_coverage": round(coverage, 4),
            "matched_count": len(matched),
            "unmatched_count": len(unmatched),
            "total_rules": len(rule_matches),
            "total_weight": total_weight,
        }

    def _generate_feedback(
        self, score: float, grade: Grade, rule_matches: list[RuleMatchDetail]
    ) -> str:
        matched = [r for r in rule_matches if r.matched]
        unmatched = [r for r in rule_matches if not r.matched]

        lines = [f"Evaluation result: {grade.value} (score={score:.2f})."]
        lines.append(f"Matched {len(matched)}/{len(rule_matches)} active rules.")

        if unmatched:
            lines.append("Unmatched rules:")
            for r in unmatched:
                lines.append(f"  - {r.rule_name}: {r.reason}")

        return "\n".join(lines)
