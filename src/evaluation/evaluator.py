"""L4 Evaluation Engine: weighted scoring and reasoning path generation."""
import logging
import uuid
from typing import Optional

from src.evaluation.models import (
    L4Rule, L4Assessment, RuleMatchDetail, ReasoningPath, Grade,
    AssessmentStatus, RuleStatus, Dimension, DimensionScore, GradeConfig,
)
from src.evaluation.rule_engine import RuleEngine

logger = logging.getLogger(__name__)


class Evaluator:
    """Evaluates design subgraphs against L4 rules, producing assessments
    with weighted scores and reasoning paths."""

    def __init__(self, rule_engine: RuleEngine, grade_config: GradeConfig = None):
        self.rule_engine = rule_engine
        self.grade_config = grade_config or GradeConfig()

    def evaluate(self, version_id: str, subgraph: dict) -> L4Assessment:
        """Evaluate a design subgraph against all active rules.

        Args:
            version_id: The design version being evaluated.
            subgraph: Dict with "nodes" and "relationships" representing the design.

        Returns:
            L4Assessment with overall score, grade, dimension scores, rule matches, and feedback.
        """
        active_rules = self.rule_engine.get_rules(status=RuleStatus.ACTIVE)
        if not active_rules:
            logger.warning("No active rules found for evaluation")
            return self._empty_assessment(version_id)

        # Group rules by dimension
        rules_by_dim: dict[Dimension, list[L4Rule]] = {d: [] for d in Dimension}
        for rule in active_rules:
            rules_by_dim[rule.dimension].append(rule)

        # Evaluate each dimension
        dimension_scores: list[DimensionScore] = []
        all_rule_matches: list[RuleMatchDetail] = []
        matched_rule_ids: list[str] = []
        unmatched_rules: list[dict] = []
        total_weighted_score = 0.0
        total_weight = 0.0

        for dim in Dimension:
            dim_rules = rules_by_dim[dim]
            if dim_rules:
                dim_score, dim_matches, dim_weight = self._evaluate_dimension(dim_rules, subgraph)
            else:
                dim_score, dim_matches, dim_weight = 0.0, [], 0.0

            matched_count = sum(1 for m in dim_matches if m.matched)
            dimension_scores.append(DimensionScore(
                dimension=dim,
                score=round(dim_score, 4),
                grade=self._score_to_grade(dim_score),
                matched_rules=matched_count,
                total_rules=len(dim_rules),
            ))

            all_rule_matches.extend(dim_matches)
            for match in dim_matches:
                if match.matched:
                    matched_rule_ids.append(match.rule_id)
                else:
                    rule = next((r for r in dim_rules if r.rule_id == match.rule_id), None)
                    if rule:
                        unmatched_rules.append({
                            "rule_id": rule.rule_id,
                            "rule_name": rule.name,
                            "dimension": dim.value,
                            "conditions": [
                                {
                                    "condition_type": d["condition_type"],
                                    "target_label": d["target_label"],
                                    "matched": d["matched"],
                                }
                                for d in []  # details not available here; kept for compatibility
                            ],
                        })

            total_weighted_score += dim_score * dim_weight
            total_weight += dim_weight

        overall_score = total_weighted_score / total_weight if total_weight > 0 else 0.0
        overall_grade = self._score_to_grade(overall_score)

        reasoning_path = ReasoningPath(
            path_id=f"path_{uuid.uuid4().hex[:8]}",
            assessment_id="",  # will be set after assessment is created
            matched_rule_ids=matched_rule_ids,
            evaluation_chain=all_rule_matches,
            aggregate_score=overall_score,
            unmatched_rules=unmatched_rules,
            confidence_factors=self._compute_confidence(all_rule_matches, total_weight),
        )

        feedback = self._generate_feedback(overall_score, overall_grade, all_rule_matches)

        assessment = L4Assessment(
            assessment_id=f"assess_{uuid.uuid4().hex[:8]}",
            version_id=version_id,
            overall_score=round(overall_score, 4),
            overall_grade=overall_grade,
            rule_matches=all_rule_matches,
            feedback_text=feedback,
            status=AssessmentStatus.PENDING_REVIEW,
            dimension_scores=dimension_scores,
            evaluation_mode="single",
        )

        # Backfill assessment_id into reasoning path
        reasoning_path.assessment_id = assessment.assessment_id

        logger.info(
            f"Evaluation complete for {version_id}: "
            f"score={overall_score:.4f}, grade={overall_grade.value}, "
            f"matched={len(matched_rule_ids)}/{len(active_rules)} rules"
        )

        return assessment

    def _evaluate_dimension(
        self, rules: list[L4Rule], subgraph: dict
    ) -> tuple[float, list[RuleMatchDetail], float]:
        """Evaluate rules within a single dimension. Returns (score, matches, total_weight)."""
        rule_matches = []
        total_weighted = 0.0
        total_weight = 0.0

        for rule in rules:
            matched_score, details = self.rule_engine.match_rule(rule, subgraph)
            is_matched = matched_score > 0
            contribution = rule.conclusion_score * rule.weight if is_matched else 0.0
            match_detail = RuleMatchDetail(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                matched=is_matched,
                score_contribution=contribution,
                matched_pattern=self._format_pattern(details),
                reason=self._format_reason(rule, is_matched, details),
            )
            rule_matches.append(match_detail)
            total_weighted += contribution
            total_weight += rule.weight

        dim_score = total_weighted / total_weight if total_weight > 0 else 0.0
        return dim_score, rule_matches, total_weight

    def _empty_assessment(self, version_id: str) -> L4Assessment:
        return L4Assessment(
            assessment_id=f"assess_{uuid.uuid4().hex[:8]}",
            version_id=version_id,
            overall_score=0.0,
            overall_grade=Grade.UNQUALIFIED,
            rule_matches=[],
            feedback_text="No active rules available for evaluation.",
            status=AssessmentStatus.PENDING_REVIEW,
        )

    def _score_to_grade(self, score: float) -> Grade:
        cfg = self.grade_config
        if score >= cfg.excellent_threshold:
            return Grade.EXCELLENT
        elif score >= cfg.good_threshold:
            return Grade.GOOD
        elif score >= cfg.qualified_threshold:
            return Grade.QUALIFIED
        return Grade.UNQUALIFIED

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
