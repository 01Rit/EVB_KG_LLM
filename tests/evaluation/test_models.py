"""Tests for L4 Evaluation Layer Pydantic Models."""
import pytest
from src.evaluation.models import (
    RuleStatus, VersionStatus, AssessmentStatus, ActionOperation,
    ActionStatus, FeedbackType, SuggestionType, Grade, Dimension,
    L4RuleCondition, L4RuleCreate, L4Rule,
    GradeStandard, ComparisonRef, FeedbackTemplate,
    DesignVersionCreate, DesignVersion, DesignVersionDetail,
    RuleMatchDetail, L4AssessmentCreate, L4Assessment,
    ReasoningPath, ExpertFeedbackCreate, ExpertFeedback,
    OptimizationActionCreate, OptimizationAction,
    DesignPredictionRequest, DesignPredictionResponse,
    RuleExtractRequest, CandidateRule,
    DimensionScore, GradeThreshold, GradeConfig,
)


# ── Enum tests ──

def test_rule_status_enum():
    assert RuleStatus.PENDING_REVIEW.value == "pending_review"
    assert RuleStatus.ACTIVE.value == "active"
    assert RuleStatus.DISABLED.value == "disabled"


def test_version_status_enum():
    assert VersionStatus.DRAFT.value == "draft"
    assert VersionStatus.EVALUATED.value == "evaluated"
    assert VersionStatus.OPTIMIZED.value == "optimized"
    assert VersionStatus.ARCHIVED.value == "archived"


def test_assessment_status_enum():
    assert AssessmentStatus.PENDING_REVIEW.value == "pending_review"
    assert AssessmentStatus.CONFIRMED.value == "confirmed"
    assert AssessmentStatus.REVISED.value == "revised"


def test_action_operation_enum():
    assert ActionOperation.ADD_NODE.value == "ADD_NODE"
    assert ActionOperation.REMOVE_NODE.value == "REMOVE_NODE"
    assert ActionOperation.MODIFY_PROPERTY.value == "MODIFY_PROPERTY"
    assert ActionOperation.ADD_REL.value == "ADD_REL"
    assert ActionOperation.REMOVE_REL.value == "REMOVE_REL"
    assert ActionOperation.SWAP_CONNECTION.value == "SWAP_CONNECTION"


def test_action_status_enum():
    assert ActionStatus.PROPOSED.value == "proposed"
    assert ActionStatus.APPLIED.value == "applied"
    assert ActionStatus.REJECTED.value == "rejected"


def test_feedback_type_enum():
    assert FeedbackType.CONFIRM.value == "confirm"
    assert FeedbackType.REVISE.value == "revise"
    assert FeedbackType.REJECT.value == "reject"
    assert FeedbackType.ADD_KNOWLEDGE.value == "add_knowledge"


def test_suggestion_type_enum():
    assert SuggestionType.IMPROVEMENT.value == "improvement"
    assert SuggestionType.WARNING.value == "warning"
    assert SuggestionType.INFO.value == "info"


def test_dimension_enum():
    assert Dimension.TECHNICAL.value == "technical"
    assert Dimension.ECONOMIC.value == "economic"
    assert Dimension.ENVIRONMENTAL.value == "environmental"


def test_grade_enum():
    assert Grade.EXCELLENT.value == "优秀"
    assert Grade.GOOD.value == "良好"
    assert Grade.QUALIFIED.value == "合格"
    assert Grade.UNQUALIFIED.value == "不可再制造"


# ── L4RuleCondition tests ──

def test_l4rule_condition_minimal():
    cond = L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接")
    assert cond.condition_type == "REQUIRES_CONNECTION"
    assert cond.target_label == "螺栓连接"
    assert cond.target_id is None
    assert cond.effect is None


def test_l4rule_condition_full():
    cond = L4RuleCondition(
        condition_type="REQUIRES_TOOL",
        target_label="标准扳手",
        target_id="tool_001",
        effect=0.3,
    )
    assert cond.target_id == "tool_001"
    assert cond.effect == 0.3


# ── L4RuleCreate tests ──

def test_l4rule_create_minimal():
    rule = L4RuleCreate(name="test_rule", conclusion_score=0.8, conclusion_grade=Grade.GOOD)
    assert rule.name == "test_rule"
    assert rule.conclusion_score == 0.8
    assert rule.conclusion_grade == Grade.GOOD
    assert rule.weight == 1.0
    assert rule.conditions == []
    assert rule.description == ""


def test_l4rule_create_with_conditions():
    conditions = [
        L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
        L4RuleCondition(condition_type="REQUIRES_TOOL", target_label="标准扳手", effect=0.2),
    ]
    rule = L4RuleCreate(
        name="bolt_rule",
        description="Requires bolt connection",
        conclusion_score=0.9,
        conclusion_grade=Grade.GOOD,
        weight=1.5,
        conditions=conditions,
        source_doc_id="doc_001",
    )
    assert len(rule.conditions) == 2
    assert rule.conditions[0].target_label == "螺栓连接"
    assert rule.source_doc_id == "doc_001"
    assert rule.weight == 1.5


def test_l4rule_create_score_validation():
    with pytest.raises(Exception):
        L4RuleCreate(name="bad", conclusion_score=1.5, conclusion_grade=Grade.GOOD)
    with pytest.raises(Exception):
        L4RuleCreate(name="bad", conclusion_score=-0.1, conclusion_grade=Grade.UNQUALIFIED)


# ── L4Rule tests ──

def test_l4rule_defaults():
    rule = L4Rule(rule_id="r001", name="test", conclusion_score=0.5, conclusion_grade=Grade.QUALIFIED)
    assert rule.status == RuleStatus.PENDING_REVIEW
    assert rule.hit_count == 0
    assert rule.created_at is None


def test_l4rule_full():
    rule = L4Rule(
        rule_id="r002",
        name="full_rule",
        description="A full rule",
        conclusion_score=0.7,
        conclusion_grade=Grade.QUALIFIED,
        weight=2.0,
        status=RuleStatus.ACTIVE,
        conditions=[L4RuleCondition(condition_type="REQUIRES_STRUCTURE", target_label="可直达")],
        source_doc_id="doc_002",
        hit_count=5,
        created_at="2026-05-20T00:00:00",
    )
    assert rule.status == RuleStatus.ACTIVE
    assert rule.hit_count == 5
    assert len(rule.conditions) == 1


# ── GradeStandard tests ──

def test_grade_standard():
    gs = GradeStandard(
        grade_id="gs001",
        name="High Grade",
        min_score=0.8,
        max_score=1.0,
        description="Excellent disassemblability",
        recommendation="Proceed with design",
    )
    assert gs.min_score == 0.8
    assert gs.max_score == 1.0


# ── ComparisonRef tests ──

def test_comparison_ref():
    ref = ComparisonRef(
        ref_id="cr001",
        name="Bolt vs Clip",
        option_a="螺栓连接",
        option_b="卡扣连接",
        advantage="option_a",
        reason="螺栓更易拆卸",
        score_diff=0.15,
    )
    assert ref.advantage == "option_a"
    assert ref.score_diff == 0.15


# ── FeedbackTemplate tests ──

def test_feedback_template():
    ft = FeedbackTemplate(
        template_id="ft001",
        name="Warning template",
        condition_pattern="score < 0.5",
        feedback_text="Score is low, consider revising",
        suggestion_type=SuggestionType.WARNING,
    )
    assert ft.suggestion_type == SuggestionType.WARNING


# ── DesignVersion tests ──

def test_design_version_create():
    dvc = DesignVersionCreate(design_name="Battery V1")
    assert dvc.design_name == "Battery V1"
    assert dvc.component_ids == []
    assert dvc.connection_ids == []


def test_design_version_create_with_ids():
    dvc = DesignVersionCreate(
        design_name="Battery V2",
        component_ids=["c1", "c2"],
        connection_ids=["conn1"],
    )
    assert len(dvc.component_ids) == 2


def test_design_version():
    dv = DesignVersion(
        version_id="v001",
        design_name="Battery V1",
        version_number=1,
    )
    assert dv.status == VersionStatus.DRAFT
    assert dv.created_by == "user"
    assert dv.component_count == 0


def test_design_version_detail():
    dvd = DesignVersionDetail(
        version_id="v002",
        design_name="Battery V2",
        version_number=2,
        components=[{"id": "c1", "label": "电池壳"}],
        connections=[{"id": "conn1", "type": "螺栓连接"}],
        relationships=[{"source": "c1", "target": "c2", "type": "CONNECTED_TO"}],
    )
    assert len(dvd.components) == 1
    assert len(dvd.connections) == 1
    assert len(dvd.relationships) == 1


# ── RuleMatchDetail tests ──

def test_rule_match_detail():
    rmd = RuleMatchDetail(
        rule_id="r001",
        rule_name="bolt_rule",
        matched=True,
        score_contribution=0.3,
        matched_pattern="螺栓连接",
        reason="Connection found",
    )
    assert rmd.matched is True
    assert rmd.score_contribution == 0.3


def test_rule_match_detail_defaults():
    rmd = RuleMatchDetail(rule_id="r002", rule_name="test", matched=False, score_contribution=0.0)
    assert rmd.matched_pattern == ""
    assert rmd.reason == ""


# ── L4Assessment tests ──

def test_l4_assessment_create():
    ac = L4AssessmentCreate(version_id="v001")
    assert ac.version_id == "v001"


def test_l4_assessment():
    matches = [
        RuleMatchDetail(rule_id="r001", rule_name="bolt", matched=True, score_contribution=0.4),
        RuleMatchDetail(rule_id="r002", rule_name="tool", matched=False, score_contribution=0.0),
    ]
    assessment = L4Assessment(
        assessment_id="a001",
        version_id="v001",
        overall_score=0.75,
        overall_grade=Grade.GOOD,
        rule_matches=matches,
        feedback_text="Good design",
        status=AssessmentStatus.PENDING_REVIEW,
    )
    assert assessment.overall_score == 0.75
    assert assessment.overall_grade == Grade.GOOD
    assert len(assessment.rule_matches) == 2
    assert assessment.rule_matches[0].matched is True


def test_l4_assessment_status():
    a = L4Assessment(
        assessment_id="a002",
        version_id="v002",
        overall_score=0.4,
        overall_grade=Grade.UNQUALIFIED,
        status=AssessmentStatus.CONFIRMED,
    )
    assert a.status == AssessmentStatus.CONFIRMED


# ── ReasoningPath tests ──

def test_reasoning_path():
    rp = ReasoningPath(
        path_id="rp001",
        assessment_id="a001",
        matched_rule_ids=["r001", "r003"],
        evaluation_chain=[
            RuleMatchDetail(rule_id="r001", rule_name="bolt", matched=True, score_contribution=0.3),
        ],
        aggregate_score=0.6,
        unmatched_rules=[{"rule_id": "r002", "reason": "no matching pattern"}],
        confidence_factors={"coverage": 0.8, "consistency": 0.9},
    )
    assert len(rp.matched_rule_ids) == 2
    assert rp.aggregate_score == 0.6
    assert rp.confidence_factors["coverage"] == 0.8


def test_reasoning_path_defaults():
    rp = ReasoningPath(path_id="rp002", assessment_id="a002")
    assert rp.matched_rule_ids == []
    assert rp.aggregate_score == 0.0


# ── ExpertFeedback tests ──

def test_expert_feedback_create():
    efc = ExpertFeedbackCreate(
        feedback_type=FeedbackType.REVISE,
        original_score=0.7,
        revised_score=0.85,
        comment="Underestimated accessibility",
        expert_name="Dr. Chen",
    )
    assert efc.feedback_type == FeedbackType.REVISE
    assert efc.revised_score == 0.85


def test_expert_feedback_create_defaults():
    efc = ExpertFeedbackCreate(feedback_type=FeedbackType.CONFIRM, original_score=0.9)
    assert efc.revised_score is None
    assert efc.comment == ""
    assert efc.expert_name == "anonymous"


def test_expert_feedback():
    ef = ExpertFeedback(
        feedback_id="ef001",
        assessment_id="a001",
        feedback_type=FeedbackType.CONFIRM,
        original_score=0.8,
    )
    assert ef.feedback_id == "ef001"
    assert ef.revised_score is None


def test_expert_feedback_add_knowledge():
    ef = ExpertFeedback(
        feedback_id="ef002",
        assessment_id="a002",
        feedback_type=FeedbackType.ADD_KNOWLEDGE,
        original_score=0.5,
        revised_score=0.6,
        comment="Added new constraint rule",
    )
    assert ef.feedback_type == FeedbackType.ADD_KNOWLEDGE


# ── OptimizationAction tests ──

def test_optimization_action_create():
    oac = OptimizationActionCreate(
        operation=ActionOperation.ADD_NODE,
        target_label="新组件",
        payload={"label": "新组件", "properties": {"type": "bracket"}},
        reason="Missing structural support",
    )
    assert oac.operation == ActionOperation.ADD_NODE
    assert oac.payload["label"] == "新组件"


def test_optimization_action_create_all_operations():
    for op in ActionOperation:
        oac = OptimizationActionCreate(operation=op)
        assert oac.operation == op


def test_optimization_action_create_defaults():
    oac = OptimizationActionCreate(operation=ActionOperation.REMOVE_REL)
    assert oac.target_label == ""
    assert oac.target_id is None
    assert oac.payload == {}
    assert oac.reason == ""


def test_optimization_action():
    oa = OptimizationAction(
        action_id="oa001",
        assessment_id="a001",
        operation=ActionOperation.MODIFY_PROPERTY,
        target_id="c001",
        payload={"property": "material", "new_value": "aluminum"},
        reason="Better recyclability",
    )
    assert oa.status == ActionStatus.PROPOSED
    assert oa.operation == ActionOperation.MODIFY_PROPERTY


def test_optimization_action_statuses():
    for status in ActionStatus:
        oa = OptimizationAction(
            action_id="oa_test",
            assessment_id="a001",
            operation=ActionOperation.ADD_REL,
            status=status,
        )
        assert oa.status == status


def test_optimization_action_swap_connection():
    oa = OptimizationAction(
        action_id="oa002",
        assessment_id="a002",
        operation=ActionOperation.SWAP_CONNECTION,
        payload={"from": "conn_a", "to": "conn_b"},
        reason="Better access path",
    )
    assert oa.operation == ActionOperation.SWAP_CONNECTION
    assert oa.payload["from"] == "conn_a"


# ── DesignPrediction tests ──

def test_design_prediction_request():
    req = DesignPredictionRequest(
        connection_types=["螺栓连接", "卡扣连接"],
        tool_requirements=["标准扳手"],
        structure_features=["可直达"],
        component_count=5,
        assembly_mode="sequential",
    )
    assert len(req.connection_types) == 2
    assert req.component_count == 5


def test_design_prediction_request_defaults():
    req = DesignPredictionRequest()
    assert req.connection_types == []
    assert req.component_count == 0
    assert req.assembly_mode == ""


def test_design_prediction_response():
    matches = [
        RuleMatchDetail(rule_id="r001", rule_name="bolt", matched=True, score_contribution=0.4),
    ]
    resp = DesignPredictionResponse(
        predicted_score=0.82,
        predicted_grade=Grade.GOOD,
        matched_rules=matches,
        risk_factors=["Complex assembly"],
        suggestions=["Use snap-fit where possible"],
    )
    assert resp.predicted_score == 0.82
    assert resp.predicted_grade == Grade.GOOD
    assert len(resp.risk_factors) == 1
    assert len(resp.suggestions) == 1


# ── Import tests ──

def test_rule_extract_request():
    req = RuleExtractRequest(doc_ids=["doc1", "doc2"])
    assert len(req.doc_ids) == 2


def test_rule_extract_request_defaults():
    req = RuleExtractRequest()
    assert req.doc_ids == []


def test_candidate_rule():
    cr = CandidateRule(
        rule_id="cr001",
        name="Extracted rule",
        description="Auto-extracted from document",
        conclusion_score=0.6,
        conclusion_grade=Grade.QUALIFIED,
        weight=1.0,
        conditions=[
            L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
        ],
        source_doc_id="doc_003",
        consistency_valid=True,
        consistency_errors=[],
    )
    assert cr.consistency_valid is True
    assert len(cr.conditions) == 1
    assert cr.conclusion_grade == Grade.QUALIFIED


def test_candidate_rule_defaults():
    cr = CandidateRule(rule_id="cr002", name="basic")
    assert cr.description == ""
    assert cr.conclusion_score == 0.5
    assert cr.conclusion_grade == Grade.QUALIFIED
    assert cr.consistency_valid is False
    assert cr.consistency_errors == []


def test_candidate_rule_with_errors():
    cr = CandidateRule(
        rule_id="cr003",
        name="bad_rule",
        consistency_valid=False,
        consistency_errors=["Score contradicts grade", "Missing target"],
    )
    assert cr.consistency_valid is False
    assert len(cr.consistency_errors) == 2


# ── Serialization tests ──

def test_l4rule_serialization():
    rule = L4Rule(
        rule_id="r001",
        name="test",
        conclusion_score=0.8,
        conclusion_grade=Grade.GOOD,
        conditions=[L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接")],
    )
    data = rule.model_dump()
    assert data["rule_id"] == "r001"
    assert data["status"] == "pending_review"
    assert data["conditions"][0]["target_label"] == "螺栓连接"


def test_l4_assessment_serialization():
    assessment = L4Assessment(
        assessment_id="a001",
        version_id="v001",
        overall_score=0.75,
        overall_grade=Grade.GOOD,
    )
    data = assessment.model_dump()
    assert data["overall_grade"] == "良好"
    assert data["status"] == "pending_review"


def test_design_prediction_response_serialization():
    resp = DesignPredictionResponse(predicted_score=0.9, predicted_grade=Grade.GOOD)
    data = resp.model_dump()
    assert data["predicted_grade"] == "良好"
    assert data["matched_rules"] == []


# ── DimensionScore tests ──

def test_dimension_score():
    ds = DimensionScore(
        dimension=Dimension.TECHNICAL,
        score=0.82,
        rsr_value=0.75,
        rank=1,
        grade=Grade.GOOD,
        matched_rules=5,
        total_rules=8,
    )
    assert ds.dimension == Dimension.TECHNICAL
    assert ds.score == 0.82
    assert ds.rsr_value == 0.75
    assert ds.rank == 1
    assert ds.grade == Grade.GOOD
    assert ds.matched_rules == 5
    assert ds.total_rules == 8


def test_dimension_score_optional_fields():
    ds = DimensionScore(
        dimension=Dimension.ECONOMIC,
        grade=Grade.QUALIFIED,
        matched_rules=2,
        total_rules=6,
    )
    assert ds.score is None
    assert ds.rsr_value is None
    assert ds.rank is None


def test_dimension_score_all_dimensions():
    for dim in Dimension:
        ds = DimensionScore(
            dimension=dim,
            grade=Grade.GOOD,
            matched_rules=3,
            total_rules=5,
        )
        assert ds.dimension == dim


# ── GradeThreshold tests ──

def test_grade_threshold():
    gt = GradeThreshold(
        excellent=0.85,
        good=0.65,
        qualified=0.45,
        regression={"min": 0.0, "max": 0.3},
    )
    assert gt.excellent == 0.85
    assert gt.good == 0.65
    assert gt.qualified == 0.45
    assert gt.regression["min"] == 0.0
    assert gt.regression["max"] == 0.3


def test_grade_threshold_empty_regression():
    gt = GradeThreshold(
        excellent=0.9,
        good=0.7,
        qualified=0.5,
        regression={},
    )
    assert gt.regression == {}


# ── GradeConfig tests ──

def test_grade_config_defaults():
    gc = GradeConfig()
    assert gc.excellent_threshold == 0.75
    assert gc.good_threshold == 0.55
    assert gc.qualified_threshold == 0.35
    assert gc.source == "default"


def test_grade_config_custom():
    gc = GradeConfig(
        excellent_threshold=0.9,
        good_threshold=0.7,
        qualified_threshold=0.5,
        source="expert_panel",
    )
    assert gc.excellent_threshold == 0.9
    assert gc.good_threshold == 0.7
    assert gc.qualified_threshold == 0.5
    assert gc.source == "expert_panel"


# ── L4RuleCondition with fuzzy_threshold ──

def test_l4rule_condition_fuzzy_threshold_default():
    cond = L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接")
    assert cond.fuzzy_threshold == 0.6


def test_l4rule_condition_custom_fuzzy_threshold():
    cond = L4RuleCondition(
        condition_type="REQUIRES_CONNECTION",
        target_label="螺栓连接",
        fuzzy_threshold=0.85,
    )
    assert cond.fuzzy_threshold == 0.85


# ── L4RuleCreate with dimension ──

def test_l4rule_create_dimension_default():
    rule = L4RuleCreate(name="test_rule", conclusion_score=0.8, conclusion_grade=Grade.GOOD)
    assert rule.dimension == Dimension.TECHNICAL


def test_l4rule_create_with_dimension():
    rule = L4RuleCreate(
        name="eco_rule",
        conclusion_score=0.6,
        conclusion_grade=Grade.QUALIFIED,
        dimension=Dimension.ENVIRONMENTAL,
    )
    assert rule.dimension == Dimension.ENVIRONMENTAL


def test_l4rule_create_economic_dimension():
    rule = L4RuleCreate(
        name="cost_rule",
        conclusion_score=0.7,
        conclusion_grade=Grade.GOOD,
        dimension=Dimension.ECONOMIC,
    )
    assert rule.dimension == Dimension.ECONOMIC


# ── L4Rule with dimension ──

def test_l4rule_dimension_default():
    rule = L4Rule(rule_id="r010", name="test", conclusion_score=0.5, conclusion_grade=Grade.QUALIFIED)
    assert rule.dimension == Dimension.TECHNICAL


def test_l4rule_with_dimension():
    rule = L4Rule(
        rule_id="r011",
        name="env_rule",
        conclusion_score=0.7,
        conclusion_grade=Grade.GOOD,
        dimension=Dimension.ENVIRONMENTAL,
    )
    assert rule.dimension == Dimension.ENVIRONMENTAL


# ── CandidateRule with new fields ──

def test_candidate_rule_new_field_defaults():
    cr = CandidateRule(rule_id="cr010", name="basic")
    assert cr.dimension == Dimension.TECHNICAL
    assert cr.fuzzy_threshold == 0.6
    assert cr.duplicate_status is None
    assert cr.duplicate_of is None


def test_candidate_rule_with_new_fields():
    cr = CandidateRule(
        rule_id="cr011",
        name="extracted_rule",
        dimension=Dimension.ECONOMIC,
        fuzzy_threshold=0.8,
        duplicate_status="duplicate",
        duplicate_of="cr001",
    )
    assert cr.dimension == Dimension.ECONOMIC
    assert cr.fuzzy_threshold == 0.8
    assert cr.duplicate_status == "duplicate"
    assert cr.duplicate_of == "cr001"


def test_candidate_rule_duplicate_status_variants():
    for status in ["duplicate", "similar", None]:
        cr = CandidateRule(
            rule_id="cr012",
            name="test",
            duplicate_status=status,
        )
        assert cr.duplicate_status == status


# ── L4Assessment with new fields ──

def test_l4_assessment_new_field_defaults():
    a = L4Assessment(
        assessment_id="a010",
        version_id="v010",
        overall_score=0.7,
        overall_grade=Grade.GOOD,
    )
    assert a.dimension_scores == []
    assert a.evaluation_mode == "single"
    assert a.dimension_weights == {}
    assert a.grade_thresholds is None
    assert a.rank_matrix is None
    assert a.per_version is None


def test_l4_assessment_with_dimension_scores():
    scores = [
        DimensionScore(
            dimension=Dimension.TECHNICAL,
            score=0.8,
            grade=Grade.GOOD,
            matched_rules=4,
            total_rules=6,
        ),
        DimensionScore(
            dimension=Dimension.ECONOMIC,
            score=0.6,
            grade=Grade.QUALIFIED,
            matched_rules=3,
            total_rules=5,
        ),
    ]
    a = L4Assessment(
        assessment_id="a011",
        version_id="v011",
        overall_score=0.7,
        overall_grade=Grade.GOOD,
        dimension_scores=scores,
    )
    assert len(a.dimension_scores) == 2
    assert a.dimension_scores[0].dimension == Dimension.TECHNICAL
    assert a.dimension_scores[1].score == 0.6


def test_l4_assessment_multi_mode():
    thresholds = GradeThreshold(
        excellent=0.85,
        good=0.65,
        qualified=0.45,
        regression={"min": 0.0, "max": 0.3},
    )
    a = L4Assessment(
        assessment_id="a012",
        version_id="v012",
        overall_score=0.72,
        overall_grade=Grade.GOOD,
        evaluation_mode="multi",
        dimension_weights={"technical": 0.5, "economic": 0.3, "environmental": 0.2},
        grade_thresholds=thresholds,
        rank_matrix=[{"version": "v1", "rank": 1}],
        per_version=[{"version_id": "v1", "score": 0.72}],
    )
    assert a.evaluation_mode == "multi"
    assert a.dimension_weights["technical"] == 0.5
    assert a.grade_thresholds.excellent == 0.85
    assert a.rank_matrix[0]["rank"] == 1
    assert a.per_version[0]["score"] == 0.72
