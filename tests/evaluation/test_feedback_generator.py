"""Tests for L4 Feedback Generator."""
import pytest
from unittest.mock import MagicMock
from src.evaluation.feedback_generator import FeedbackGenerator
from src.evaluation.models import (
    L4Assessment, RuleMatchDetail, L4Rule, L4RuleCondition,
    Grade, AssessmentStatus, RuleStatus, SuggestionType,
)


@pytest.fixture
def generator():
    return FeedbackGenerator(llm_client=None)


@pytest.fixture
def sample_rules():
    return [
        L4Rule(
            rule_id="rule_001",
            name="螺栓连接易拆卸",
            conclusion_score=0.8,
            conclusion_grade=Grade.GOOD,
            weight=1.0,
            status=RuleStatus.ACTIVE,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            ],
        ),
        L4Rule(
            rule_id="rule_002",
            name="工具通用性",
            conclusion_score=0.6,
            conclusion_grade=Grade.QUALIFIED,
            weight=1.0,
            status=RuleStatus.ACTIVE,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_TOOL", target_label="标准扳手"),
            ],
        ),
    ]


def _make_assessment(grade: Grade, score: float, matches: list[RuleMatchDetail]) -> L4Assessment:
    return L4Assessment(
        assessment_id="assess_test",
        version_id="v1",
        overall_score=score,
        overall_grade=grade,
        rule_matches=matches,
        feedback_text="test feedback",
        status=AssessmentStatus.PENDING_REVIEW,
    )


# ── Summary Tests ──


class TestSummary:
    def test_high_grade_summary(self, generator, sample_rules):
        assessment = _make_assessment(Grade.GOOD, 0.85, [
            RuleMatchDetail(rule_id="rule_001", rule_name="螺栓连接易拆卸", matched=True, score_contribution=0.8),
            RuleMatchDetail(rule_id="rule_002", rule_name="工具通用性", matched=True, score_contribution=0.6),
        ])
        result = generator.generate(assessment, sample_rules)
        assert "良好" in result["summary"]
        assert "2" in result["summary"]
        assert "0.85" in result["summary"]

    def test_medium_grade_summary(self, generator, sample_rules):
        assessment = _make_assessment(Grade.QUALIFIED, 0.5, [
            RuleMatchDetail(rule_id="rule_001", rule_name="螺栓连接易拆卸", matched=True, score_contribution=0.8),
            RuleMatchDetail(rule_id="rule_002", rule_name="工具通用性", matched=False, score_contribution=0.0),
        ])
        result = generator.generate(assessment, sample_rules)
        assert "合格" in result["summary"]

    def test_low_grade_summary(self, generator, sample_rules):
        assessment = _make_assessment(Grade.UNQUALIFIED, 0.2, [
            RuleMatchDetail(rule_id="rule_001", rule_name="螺栓连接易拆卸", matched=False, score_contribution=0.0),
            RuleMatchDetail(rule_id="rule_002", rule_name="工具通用性", matched=False, score_contribution=0.0),
        ])
        result = generator.generate(assessment, sample_rules)
        assert "需改进" in result["summary"]


# ── Suggestion Tests ──


class TestSuggestions:
    def test_suggestions_for_unmatched(self, generator, sample_rules):
        assessment = _make_assessment(Grade.QUALIFIED, 0.5, [
            RuleMatchDetail(rule_id="rule_001", rule_name="螺栓连接易拆卸", matched=True, score_contribution=0.8),
            RuleMatchDetail(
                rule_id="rule_002", rule_name="工具通用性",
                matched=False, score_contribution=0.0,
                reason="Rule '工具通用性' failed on: 标准扳手",
            ),
        ])
        result = generator.generate(assessment, sample_rules)
        assert len(result["suggestions"]) == 1
        s = result["suggestions"][0]
        assert s["rule_id"] == "rule_002"
        assert s["type"] == SuggestionType.IMPROVEMENT.value
        assert len(s["conditions"]) == 1
        assert s["conditions"][0]["target_label"] == "标准扳手"

    def test_no_suggestions_when_all_match(self, generator, sample_rules):
        assessment = _make_assessment(Grade.GOOD, 0.85, [
            RuleMatchDetail(rule_id="rule_001", rule_name="螺栓连接易拆卸", matched=True, score_contribution=0.8),
            RuleMatchDetail(rule_id="rule_002", rule_name="工具通用性", matched=True, score_contribution=0.6),
        ])
        result = generator.generate(assessment, sample_rules)
        assert result["suggestions"] == []


# ── Risk Tests ──


class TestRisks:
    def test_low_grade_risk(self, generator, sample_rules):
        assessment = _make_assessment(Grade.UNQUALIFIED, 0.2, [
            RuleMatchDetail(rule_id="rule_001", rule_name="螺栓连接易拆卸", matched=False, score_contribution=0.0),
            RuleMatchDetail(rule_id="rule_002", rule_name="工具通用性", matched=False, score_contribution=0.0),
        ])
        result = generator.generate(assessment, sample_rules)
        high_risks = [r for r in result["risks"] if r["level"] == "high"]
        assert len(high_risks) == 1
        assert "全面审查" in high_risks[0]["message"]

    def test_high_weight_unmatched_risk(self, generator, sample_rules):
        assessment = _make_assessment(Grade.QUALIFIED, 0.4, [
            RuleMatchDetail(rule_id="rule_001", rule_name="螺栓连接易拆卸", matched=False, score_contribution=0.0),
            RuleMatchDetail(rule_id="rule_002", rule_name="工具通用性", matched=True, score_contribution=0.6),
        ])
        result = generator.generate(assessment, sample_rules)
        medium_risks = [r for r in result["risks"] if r["level"] == "medium"]
        assert len(medium_risks) == 1
        assert "螺栓连接易拆卸" in medium_risks[0]["message"]

    def test_no_risks_when_good(self, generator, sample_rules):
        assessment = _make_assessment(Grade.GOOD, 0.85, [
            RuleMatchDetail(rule_id="rule_001", rule_name="螺栓连接易拆卸", matched=True, score_contribution=0.8),
            RuleMatchDetail(rule_id="rule_002", rule_name="工具通用性", matched=True, score_contribution=0.6),
        ])
        result = generator.generate(assessment, sample_rules)
        assert result["risks"] == []


# ── Raw Feedback Passthrough ──


class TestRawFeedback:
    def test_raw_feedback_included(self, generator, sample_rules):
        assessment = _make_assessment(Grade.GOOD, 0.85, [])
        assessment.feedback_text = "原始反馈内容"
        result = generator.generate(assessment, sample_rules)
        assert result["raw_feedback"] == "原始反馈内容"


# ── LLM Feedback ──


class TestLLMFeedback:
    def test_llm_feedback_success(self, sample_rules):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "LLM生成的反馈意见"
        gen = FeedbackGenerator(llm_client=mock_llm)

        assessment = _make_assessment(Grade.QUALIFIED, 0.5, [
            RuleMatchDetail(rule_id="rule_001", rule_name="螺栓连接易拆卸", matched=True, score_contribution=0.8),
            RuleMatchDetail(rule_id="rule_002", rule_name="工具通用性", matched=False, score_contribution=0.0),
        ])
        result = gen.generate(assessment, sample_rules)
        assert result["llm_feedback"] == "LLM生成的反馈意见"
        mock_llm.generate.assert_called_once()

    def test_llm_feedback_failure_graceful(self, sample_rules):
        mock_llm = MagicMock()
        mock_llm.generate.side_effect = Exception("LLM error")
        gen = FeedbackGenerator(llm_client=mock_llm)

        assessment = _make_assessment(Grade.GOOD, 0.85, [
            RuleMatchDetail(rule_id="rule_001", rule_name="螺栓连接易拆卸", matched=True, score_contribution=0.8),
        ])
        result = gen.generate(assessment, sample_rules)
        assert result["llm_feedback"] is None
        assert "summary" in result  # still generates non-LLM feedback

    def test_no_llm_client(self, generator, sample_rules):
        assessment = _make_assessment(Grade.GOOD, 0.85, [])
        result = generator.generate(assessment, sample_rules)
        assert "llm_feedback" not in result
