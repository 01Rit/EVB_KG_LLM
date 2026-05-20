"""Tests for L4 Evaluator: weighted scoring and reasoning path generation."""
import pytest
from src.evaluation.evaluator import Evaluator
from src.evaluation.rule_engine import RuleEngine
from src.evaluation.models import (
    L4RuleCreate, L4RuleCondition, RuleStatus, Grade, AssessmentStatus,
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
        assert assessment.overall_grade == Grade.LOW
        assert assessment.rule_matches == []
        assert "No active rules" in assessment.feedback_text
        assert assessment.status == AssessmentStatus.PENDING_REVIEW

    def test_only_disabled_rules(self, engine, evaluator, subgraph):
        rule = engine.create_rule(L4RuleCreate(
            name="disabled", conclusion_score=0.9, conclusion_grade=Grade.HIGH,
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
            conclusion_grade=Grade.HIGH,
            weight=1.0,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            ],
        ))
        assessment = evaluator.evaluate("v1", subgraph)
        assert assessment.overall_score == 0.8
        assert assessment.overall_grade == Grade.HIGH
        assert len(assessment.rule_matches) == 1
        assert assessment.rule_matches[0].matched is True
        assert assessment.rule_matches[0].score_contribution == 0.8

    def test_all_rules_match(self, engine, evaluator, subgraph):
        engine.create_rule(L4RuleCreate(
            name="螺栓易拆",
            conclusion_score=0.8,
            conclusion_grade=Grade.HIGH,
            weight=1.0,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            ],
        ))
        engine.create_rule(L4RuleCreate(
            name="工具通用",
            conclusion_score=0.6,
            conclusion_grade=Grade.MEDIUM,
            weight=1.0,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_TOOL", target_label="标准扳手"),
            ],
        ))
        assessment = evaluator.evaluate("v1", subgraph)
        # weighted average: (0.8*1.0 + 0.6*1.0) / 2.0 = 0.7
        assert assessment.overall_score == 0.7
        assert assessment.overall_grade == Grade.HIGH
        assert all(m.matched for m in assessment.rule_matches)


# ── Partial Match ──


class TestPartialMatch:
    def test_one_matches_one_fails(self, engine, evaluator, subgraph):
        engine.create_rule(L4RuleCreate(
            name="螺栓易拆",
            conclusion_score=0.8,
            conclusion_grade=Grade.HIGH,
            weight=1.0,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            ],
        ))
        engine.create_rule(L4RuleCreate(
            name="焊接难拆",
            conclusion_score=0.3,
            conclusion_grade=Grade.LOW,
            weight=1.0,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="焊接连接"),
            ],
        ))
        assessment = evaluator.evaluate("v1", subgraph)
        # Only first rule matches: 0.8*1.0 / 2.0 = 0.4
        assert assessment.overall_score == 0.4
        assert assessment.overall_grade == Grade.MEDIUM
        assert assessment.rule_matches[0].matched is True
        assert assessment.rule_matches[1].matched is False

    def test_multi_condition_partial(self, engine, evaluator, subgraph):
        engine.create_rule(L4RuleCreate(
            name="multi",
            conclusion_score=0.9,
            conclusion_grade=Grade.HIGH,
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
            conclusion_grade=Grade.HIGH,
            weight=3.0,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            ],
        ))
        engine.create_rule(L4RuleCreate(
            name="次要规则",
            conclusion_score=0.5,
            conclusion_grade=Grade.MEDIUM,
            weight=1.0,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_TOOL", target_label="标准扳手"),
            ],
        ))
        assessment = evaluator.evaluate("v1", subgraph)
        # (1.0*3.0 + 0.5*1.0) / (3.0 + 1.0) = 3.5/4.0 = 0.875
        assert abs(assessment.overall_score - 0.875) < 0.001
        assert assessment.overall_grade == Grade.HIGH

    def test_grade_boundaries(self, engine, evaluator, subgraph):
        # Test MEDIUM boundary (score >= 0.4, < 0.7)
        engine.create_rule(L4RuleCreate(
            name="medium_rule",
            conclusion_score=0.5,
            conclusion_grade=Grade.MEDIUM,
            weight=1.0,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            ],
        ))
        assessment = evaluator.evaluate("v1", subgraph)
        assert assessment.overall_score == 0.5
        assert assessment.overall_grade == Grade.MEDIUM


# ── Reasoning Path ──


class TestReasoningPath:
    def test_matched_rule_ids(self, engine, evaluator, subgraph):
        engine.create_rule(L4RuleCreate(
            name="r1",
            conclusion_score=0.8,
            conclusion_grade=Grade.HIGH,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            ],
        ))
        engine.create_rule(L4RuleCreate(
            name="r2",
            conclusion_score=0.5,
            conclusion_grade=Grade.MEDIUM,
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
            conclusion_grade=Grade.HIGH,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            ],
        ))
        engine.create_rule(L4RuleCreate(
            name="r2",
            conclusion_score=0.5,
            conclusion_grade=Grade.MEDIUM,
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
    def test_rule_with_no_conditions_always_matches(self, engine, evaluator, subgraph):
        engine.create_rule(L4RuleCreate(
            name="默认规则",
            conclusion_score=0.5,
            conclusion_grade=Grade.MEDIUM,
            conditions=[],
        ))
        assessment = evaluator.evaluate("v1", subgraph)
        assert assessment.overall_score == 0.5
        assert assessment.rule_matches[0].matched is True


# ── Feedback ──


class TestFeedback:
    def test_feedback_contains_grade(self, engine, evaluator, subgraph):
        engine.create_rule(L4RuleCreate(
            name="r1",
            conclusion_score=0.8,
            conclusion_grade=Grade.HIGH,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            ],
        ))
        assessment = evaluator.evaluate("v1", subgraph)
        assert "高" in assessment.feedback_text
        assert "1/1" in assessment.feedback_text

    def test_feedback_lists_unmatched(self, engine, evaluator, subgraph):
        engine.create_rule(L4RuleCreate(
            name="失败规则",
            conclusion_score=0.5,
            conclusion_grade=Grade.MEDIUM,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="焊接连接"),
            ],
        ))
        assessment = evaluator.evaluate("v1", subgraph)
        assert "失败规则" in assessment.feedback_text
        assert "Unmatched" in assessment.feedback_text
