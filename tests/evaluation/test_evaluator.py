"""Tests for L4 Evaluator: weighted scoring and reasoning path generation."""
import pytest
from src.evaluation.evaluator import Evaluator
from src.evaluation.rule_engine import RuleEngine
from src.evaluation.models import (
    L4RuleCreate, L4RuleCondition, RuleStatus, Grade, AssessmentStatus,
    Dimension, GradeConfig,
)


class MockNeo4jClient:
    def execute_query(self, query, params=None):
        return []


@pytest.fixture
def engine():
    return RuleEngine(neo4j_client=MockNeo4jClient())


@pytest.fixture
def evaluator(engine):
    return Evaluator(rule_engine=engine)


@pytest.fixture
def subgraph():
    return {
        "nodes": [
            {"id": "n1", "name": "电池外壳", "label": "Component"},
            {"id": "n2", "name": "螺栓连接", "label": "Connection"},
            {"id": "n3", "name": "标准扳手", "label": "Tool"},
        ],
        "relationships": [
            {"start": "n1", "end": "n2", "type": "USES_CONNECTION"},
            {"start": "n1", "end": "n3", "type": "REQUIRES_TOOL"},
        ],
    }


# ── Empty Rules ──


class TestEmptyRules:
    def test_no_active_rules(self, evaluator, subgraph):
        assessment = evaluator.evaluate("v1", subgraph)
        assert assessment.overall_score == 0.0
        assert assessment.overall_grade == Grade.UNQUALIFIED
        assert assessment.rule_matches == []
        assert "No active rules" in assessment.feedback_text
        assert assessment.status == AssessmentStatus.PENDING_REVIEW

    def test_only_disabled_rules(self, engine, evaluator, subgraph):
        rule = engine.create_rule(L4RuleCreate(
            name="disabled", conclusion_score=0.9, conclusion_grade=Grade.GOOD,
        ))
        engine.update_rule(rule.rule_id, status=RuleStatus.DISABLED)
        assessment = evaluator.evaluate("v1", subgraph)
        assert assessment.overall_score == 0.0


# ── Full Match ──


class TestFullMatch:
    def test_single_rule_match(self, engine, evaluator, subgraph):
        engine.create_rule(L4RuleCreate(
            name="螺栓易拆",
            conclusion_score=0.8,
            conclusion_grade=Grade.GOOD,
            weight=1.0,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            ],
        ))
        assessment = evaluator.evaluate("v1", subgraph)
        # score_contribution = conclusion_score * weight = 0.8; overall = 0.8
        assert assessment.overall_score == 0.8
        assert assessment.overall_grade == Grade.EXCELLENT
        assert len(assessment.rule_matches) == 1
        assert assessment.rule_matches[0].matched is True
        assert assessment.rule_matches[0].score_contribution == 0.8

    def test_all_rules_match(self, engine, evaluator, subgraph):
        engine.create_rule(L4RuleCreate(
            name="螺栓易拆",
            conclusion_score=0.8,
            conclusion_grade=Grade.GOOD,
            weight=1.0,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            ],
        ))
        engine.create_rule(L4RuleCreate(
            name="工具通用",
            conclusion_score=0.6,
            conclusion_grade=Grade.QUALIFIED,
            weight=1.0,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_TOOL", target_label="标准扳手"),
            ],
        ))
        assessment = evaluator.evaluate("v1", subgraph)
        # TECHNICAL dim: (0.8*1.0 + 0.6*1.0) / (1.0+1.0) = 0.7
        assert assessment.overall_score == 0.7
        assert assessment.overall_grade == Grade.GOOD
        assert all(m.matched for m in assessment.rule_matches)


# ── Partial Match ──


class TestPartialMatch:
    def test_one_matches_one_fails(self, engine, evaluator, subgraph):
        engine.create_rule(L4RuleCreate(
            name="螺栓易拆",
            conclusion_score=0.8,
            conclusion_grade=Grade.GOOD,
            weight=1.0,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            ],
        ))
        engine.create_rule(L4RuleCreate(
            name="焊接难拆",
            conclusion_score=0.3,
            conclusion_grade=Grade.UNQUALIFIED,
            weight=1.0,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="焊接连接"),
            ],
        ))
        assessment = evaluator.evaluate("v1", subgraph)
        # TECHNICAL dim: first matches (0.8*1.0), second fails (0.0); score = 0.8/2.0 = 0.4
        assert assessment.overall_score == 0.4
        assert assessment.overall_grade == Grade.QUALIFIED
        assert assessment.rule_matches[0].matched is True
        assert assessment.rule_matches[0].score_contribution == 0.8
        assert assessment.rule_matches[1].matched is False
        assert assessment.rule_matches[1].score_contribution == 0.0

    def test_multi_condition_partial(self, engine, evaluator, subgraph):
        engine.create_rule(L4RuleCreate(
            name="multi",
            conclusion_score=0.9,
            conclusion_grade=Grade.GOOD,
            weight=1.0,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="卡扣连接"),
            ],
        ))
        assessment = evaluator.evaluate("v1", subgraph)
        # Rule fails because not all conditions match
        assert assessment.overall_score == 0.0
        assert assessment.rule_matches[0].matched is False


# ── Weighted Scoring ──


class TestWeightedScoring:
    def test_different_weights(self, engine, evaluator, subgraph):
        engine.create_rule(L4RuleCreate(
            name="重要规则",
            conclusion_score=1.0,
            conclusion_grade=Grade.GOOD,
            weight=3.0,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            ],
        ))
        engine.create_rule(L4RuleCreate(
            name="次要规则",
            conclusion_score=0.5,
            conclusion_grade=Grade.QUALIFIED,
            weight=1.0,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_TOOL", target_label="标准扳手"),
            ],
        ))
        assessment = evaluator.evaluate("v1", subgraph)
        # TECHNICAL dim: (1.0*3.0 + 0.5*1.0) / (3.0+1.0) = 0.875
        assert abs(assessment.overall_score - 0.875) < 0.001
        assert assessment.overall_grade == Grade.EXCELLENT

    def test_grade_boundaries(self, engine, evaluator):
        # Test _score_to_grade with default GradeConfig thresholds (0.75/0.55/0.35)
        assert evaluator._score_to_grade(0.9) == Grade.EXCELLENT
        assert evaluator._score_to_grade(0.75) == Grade.EXCELLENT
        assert evaluator._score_to_grade(0.7) == Grade.GOOD
        assert evaluator._score_to_grade(0.55) == Grade.GOOD
        assert evaluator._score_to_grade(0.5) == Grade.QUALIFIED
        assert evaluator._score_to_grade(0.35) == Grade.QUALIFIED
        assert evaluator._score_to_grade(0.3) == Grade.UNQUALIFIED
        assert evaluator._score_to_grade(0.0) == Grade.UNQUALIFIED


# ── Reasoning Path ──


class TestReasoningPath:
    def test_matched_rule_ids(self, engine, evaluator, subgraph):
        engine.create_rule(L4RuleCreate(
            name="r1",
            conclusion_score=0.8,
            conclusion_grade=Grade.GOOD,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            ],
        ))
        engine.create_rule(L4RuleCreate(
            name="r2",
            conclusion_score=0.5,
            conclusion_grade=Grade.QUALIFIED,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="焊接连接"),
            ],
        ))
        # Evaluate and check assessment rule_matches directly
        assessment = evaluator.evaluate("v1", subgraph)
        matched_ids = [m.rule_id for m in assessment.rule_matches if m.matched]
        unmatched_ids = [m.rule_id for m in assessment.rule_matches if not m.matched]
        assert len(matched_ids) == 1
        assert len(unmatched_ids) == 1

    def test_confidence_factors(self, engine, evaluator, subgraph):
        engine.create_rule(L4RuleCreate(
            name="r1",
            conclusion_score=0.8,
            conclusion_grade=Grade.GOOD,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            ],
        ))
        engine.create_rule(L4RuleCreate(
            name="r2",
            conclusion_score=0.5,
            conclusion_grade=Grade.QUALIFIED,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="焊接连接"),
            ],
        ))
        assessment = evaluator.evaluate("v1", subgraph)
        # Check rule match details include pattern and reason
        for m in assessment.rule_matches:
            assert m.rule_id != ""
            assert m.rule_name != ""
            if m.matched:
                assert m.score_contribution > 0
                assert "fully matched" in m.reason
            else:
                assert m.score_contribution == 0
                assert "failed on" in m.reason


# ── No Conditions Rule ──


class TestNoConditions:
    def test_rule_with_no_conditions(self, engine, evaluator, subgraph):
        engine.create_rule(L4RuleCreate(
            name="默认规则",
            conclusion_score=0.5,
            conclusion_grade=Grade.QUALIFIED,
            conditions=[],
        ))
        assessment = evaluator.evaluate("v1", subgraph)
        # No conditions → match_rule returns (0.0, []); matched_score=0.0 → not matched
        assert assessment.overall_score == 0.0
        assert assessment.rule_matches[0].matched is False
        assert assessment.rule_matches[0].score_contribution == 0.0


# ── Feedback ──


class TestFeedback:
    def test_feedback_contains_grade(self, engine, evaluator, subgraph):
        engine.create_rule(L4RuleCreate(
            name="r1",
            conclusion_score=0.8,
            conclusion_grade=Grade.GOOD,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            ],
        ))
        assessment = evaluator.evaluate("v1", subgraph)
        # score=0.8 >= 0.75 (excellent_threshold), grade=EXCELLENT ("优秀")
        assert "优秀" in assessment.feedback_text
        assert "1/1" in assessment.feedback_text

    def test_feedback_lists_unmatched(self, engine, evaluator, subgraph):
        engine.create_rule(L4RuleCreate(
            name="失败规则",
            conclusion_score=0.5,
            conclusion_grade=Grade.QUALIFIED,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="焊接连接"),
            ],
        ))
        assessment = evaluator.evaluate("v1", subgraph)
        assert "失败规则" in assessment.feedback_text
        assert "Unmatched" in assessment.feedback_text


# ── Dimension-Grouped Evaluation ──


class TestDimensionScores:
    def test_dimension_scores_present(self, engine, evaluator, subgraph):
        # Create rules in different dimensions
        engine.create_rule(L4RuleCreate(
            name="tech_rule",
            conclusion_score=0.8,
            conclusion_grade=Grade.GOOD,
            weight=1.0,
            dimension=Dimension.TECHNICAL,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            ],
        ))
        engine.create_rule(L4RuleCreate(
            name="econ_rule",
            conclusion_score=0.6,
            conclusion_grade=Grade.QUALIFIED,
            weight=1.0,
            dimension=Dimension.ECONOMIC,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_TOOL", target_label="标准扳手"),
            ],
        ))
        engine.create_rule(L4RuleCreate(
            name="env_rule",
            conclusion_score=0.5,
            conclusion_grade=Grade.QUALIFIED,
            weight=1.0,
            dimension=Dimension.ENVIRONMENTAL,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            ],
        ))
        assessment = evaluator.evaluate("v1", subgraph)
        # Should have 3 dimension scores (one per dimension)
        assert len(assessment.dimension_scores) == 3
        assert assessment.evaluation_mode == "single"

        # Find technical dimension score: conclusion_score=0.8, weight=1.0 -> dim_score=0.8
        tech_ds = next(ds for ds in assessment.dimension_scores if ds.dimension == Dimension.TECHNICAL)
        assert tech_ds.score == 0.8
        assert tech_ds.matched_rules == 1
        assert tech_ds.total_rules == 1
        assert tech_ds.grade == Grade.EXCELLENT  # 0.8 >= 0.75

        # Find economic dimension score: conclusion_score=0.6, weight=1.0 -> dim_score=0.6
        econ_ds = next(ds for ds in assessment.dimension_scores if ds.dimension == Dimension.ECONOMIC)
        assert econ_ds.score == 0.6
        assert econ_ds.matched_rules == 1
        assert econ_ds.total_rules == 1
        assert econ_ds.grade == Grade.GOOD  # 0.55 <= 0.6 < 0.75

        # Find environmental dimension score: conclusion_score=0.5, weight=1.0 -> dim_score=0.5
        env_ds = next(ds for ds in assessment.dimension_scores if ds.dimension == Dimension.ENVIRONMENTAL)
        assert env_ds.score == 0.5
        assert env_ds.matched_rules == 1
        assert env_ds.total_rules == 1
        assert env_ds.grade == Grade.QUALIFIED  # 0.35 <= 0.5 < 0.55

    def test_dimension_score_zero_when_no_rules(self, engine, evaluator, subgraph):
        # Create only a TECHNICAL rule
        engine.create_rule(L4RuleCreate(
            name="tech_only",
            conclusion_score=0.8,
            conclusion_grade=Grade.GOOD,
            weight=1.0,
            dimension=Dimension.TECHNICAL,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            ],
        ))
        assessment = evaluator.evaluate("v1", subgraph)
        assert len(assessment.dimension_scores) == 3

        econ_ds = next(ds for ds in assessment.dimension_scores if ds.dimension == Dimension.ECONOMIC)
        assert econ_ds.score == 0.0
        assert econ_ds.matched_rules == 0
        assert econ_ds.total_rules == 0
        assert econ_ds.grade == Grade.UNQUALIFIED

        env_ds = next(ds for ds in assessment.dimension_scores if ds.dimension == Dimension.ENVIRONMENTAL)
        assert env_ds.score == 0.0
        assert env_ds.matched_rules == 0
        assert env_ds.total_rules == 0
        assert env_ds.grade == Grade.UNQUALIFIED

    def test_overall_score_is_weighted_average_of_dimensions(self, engine, evaluator, subgraph):
        # TECHNICAL: one matched rule (conclusion_score=0.8, weight=1.0) → dim_score=0.8
        engine.create_rule(L4RuleCreate(
            name="tech_rule",
            conclusion_score=0.8,
            conclusion_grade=Grade.GOOD,
            weight=1.0,
            dimension=Dimension.TECHNICAL,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            ],
        ))
        # ECONOMIC: one unmatched rule → dim_score=0.0, dim_weight=1.0
        engine.create_rule(L4RuleCreate(
            name="econ_rule",
            conclusion_score=0.5,
            conclusion_grade=Grade.QUALIFIED,
            weight=1.0,
            dimension=Dimension.ECONOMIC,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="焊接连接"),
            ],
        ))
        assessment = evaluator.evaluate("v1", subgraph)
        # TECHNICAL dim: 0.8, weight 1.0; ECONOMIC dim: 0.0, weight 1.0; ENV dim: 0.0, weight 0.0
        # overall = (0.8*1.0 + 0.0*1.0 + 0.0*0.0) / (1.0 + 1.0 + 0.0) = 0.4
        assert assessment.overall_score == 0.4
        assert assessment.overall_grade == Grade.QUALIFIED

    def test_custom_grade_config(self, engine, subgraph):
        # Use custom thresholds
        custom_config = GradeConfig(
            excellent_threshold=0.9,
            good_threshold=0.7,
            qualified_threshold=0.5,
        )
        custom_evaluator = Evaluator(rule_engine=engine, grade_config=custom_config)
        engine.create_rule(L4RuleCreate(
            name="r1",
            conclusion_score=0.8,
            conclusion_grade=Grade.GOOD,
            weight=1.0,
            dimension=Dimension.TECHNICAL,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            ],
        ))
        assessment = custom_evaluator.evaluate("v1", subgraph)
        # score=0.8, excellent_threshold=0.9 → 0.8 < 0.9 → GOOD (0.8 >= 0.7)
        assert assessment.overall_grade == Grade.GOOD

        # Test boundary: score 0.8 with custom config (good_threshold=0.7)
        assert custom_evaluator._score_to_grade(0.8) == Grade.GOOD
        assert custom_evaluator._score_to_grade(0.6) == Grade.QUALIFIED
        assert custom_evaluator._score_to_grade(0.4) == Grade.UNQUALIFIED
