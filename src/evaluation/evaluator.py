"""L4 Evaluation Engine: weighted scoring and reasoning path generation."""
import logging
import uuid
from typing import Optional

from src.evaluation.models import (
    L4Rule, L4Assessment, RuleMatchDetail, ReasoningPath, Grade,
    AssessmentStatus, RuleStatus, Dimension, DimensionScore, GradeConfig,
    GradeThreshold,
)
from src.evaluation.rule_engine import RuleEngine
from src.evaluation.rsr import compute_dimension_rsr, compute_total_rsr, compute_dynamic_thresholds

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

    def batch_evaluate(self, subgraphs: dict[str, dict]) -> list[L4Assessment]:
        """Evaluate multiple versions using RSR method.

        Args:
            subgraphs: {version_id: subgraph_dict}

        Returns:
            List of L4Assessment, one per version, with RSR-based scores and dynamic grading.
        """
        active_rules = self.rule_engine.get_rules(status=RuleStatus.ACTIVE)
        if not active_rules:
            return [self._empty_assessment(vid) for vid in subgraphs]

        version_ids = list(subgraphs.keys())
        l = len(version_ids)

        # Group rules by dimension
        dim_rule_map: dict[Dimension, list] = {d: [] for d in Dimension}
        for rule in active_rules:
            dim_rule_map[rule.dimension].append(rule)

        # Step 1: Collect per-rule match scores once (avoids calling match_rule twice)
        # match_cache[vid][rule_id] = (score, details)
        match_cache: dict[str, dict[str, tuple[float, list[dict]]]] = {}
        for vid, sg in subgraphs.items():
            match_cache[vid] = {}
            for rule in active_rules:
                score, details = self.rule_engine.match_rule(rule, sg)
                match_cache[vid][rule.rule_id] = (score, details)

        # Step 2: Build single-mode dimension scores from cached results
        single_dim_scores: dict[str, dict[Dimension, dict]] = {}
        for vid in version_ids:
            single_dim_scores[vid] = {}
            for dim in Dimension:
                dim_rules = dim_rule_map[dim]
                total_weighted = 0.0
                total_weight = 0.0
                matched_count = 0
                for rule in dim_rules:
                    score, _ = match_cache[vid][rule.rule_id]
                    is_matched = score > 0
                    if is_matched:
                        total_weighted += rule.conclusion_score * rule.weight
                        matched_count += 1
                    total_weight += rule.weight
                dim_score = total_weighted / total_weight if total_weight > 0 else 0.0
                single_dim_scores[vid][dim] = {
                    "score": dim_score,
                    "matched_rules": matched_count,
                    "total_rules": len(dim_rules),
                }

        # Step 3: Compute RSR per dimension
        dim_rsrs: dict[Dimension, list[float]] = {}
        for dim in Dimension:
            dim_rules = dim_rule_map[dim]
            if not dim_rules:
                dim_rsrs[dim] = [0.0] * l
                continue
            scores = []
            for vid in version_ids:
                rule_scores = [match_cache[vid][rule.rule_id][0] for rule in dim_rules]
                scores.append(rule_scores)
            weights = [r.weight for r in dim_rules]
            dim_rsrs[dim] = compute_dimension_rsr(scores, weights)

        # Step 4: Hierarchical synthesis across dimensions
        dim_rsr_matrix = [dim_rsrs[dim] for dim in Dimension]
        dim_weights = [1.0 / 3, 1.0 / 3, 1.0 / 3]
        total_rsrs = compute_total_rsr(dim_rsr_matrix, dim_weights)

        # Step 5: Dynamic thresholds (total-level for overall grade, per-dimension for dimension grades)
        total_thresholds = compute_dynamic_thresholds(total_rsrs)
        dim_thresholds: dict[Dimension, dict] = {}
        for dim in Dimension:
            if dim_rule_map[dim]:
                dim_thresholds[dim] = compute_dynamic_thresholds(dim_rsrs[dim])
            else:
                dim_thresholds[dim] = total_thresholds

        # Step 6: Build batch assessments
        results = []
        for idx, vid in enumerate(version_ids):
            dim_scores = []
            for dim in Dimension:
                dt = dim_thresholds.get(dim, total_thresholds)
                grade = self._rsr_to_grade(dim_rsrs[dim][idx], dt)
                info = single_dim_scores[vid][dim]
                dim_scores.append(DimensionScore(
                    dimension=dim,
                    rsr_value=round(dim_rsrs[dim][idx], 4),
                    rank=self._compute_rank(dim_rsrs[dim], idx),
                    grade=grade,
                    matched_rules=info["matched_rules"],
                    total_rules=info["total_rules"],
                ))

            overall_grade = self._rsr_to_grade(total_rsrs[idx], total_thresholds)
            assessment = L4Assessment(
                assessment_id=f"batch_{uuid.uuid4().hex[:8]}",
                version_id=vid,
                overall_score=round(total_rsrs[idx], 4),
                overall_grade=overall_grade,
                dimension_scores=dim_scores,
                evaluation_mode="batch",
                grade_thresholds=GradeThreshold(
                    excellent=total_thresholds["excellent"],
                    good=total_thresholds["good"],
                    qualified=total_thresholds["qualified"],
                    regression=total_thresholds["regression"],
                ),
            )
            results.append(assessment)

        return results

    def _rsr_to_grade(self, rsr_value: float, thresholds: dict) -> Grade:
        """Convert RSR value to grade using dynamic thresholds."""
        if rsr_value >= thresholds["excellent"]:
            return Grade.EXCELLENT
        elif rsr_value >= thresholds["good"]:
            return Grade.GOOD
        elif rsr_value >= thresholds["qualified"]:
            return Grade.QUALIFIED
        return Grade.UNQUALIFIED

    def _compute_rank(self, values: list[float], idx: int) -> int:
        """Compute rank (1-based, highest=1) of values[idx] within the list."""
        return 1 + sum(1 for i, v in enumerate(values) if i != idx and v > values[idx])

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
