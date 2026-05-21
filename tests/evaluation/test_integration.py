"""Integration tests for the L4 evaluation closed-loop system."""
import pytest
from src.evaluation.closed_loop import ClosedLoop
from src.evaluation.models import (
    DesignVersionCreate, L4RuleCreate, L4RuleCondition,
    ExpertFeedbackCreate, Grade, FeedbackType, ActionOperation,
    ActionStatus, AssessmentStatus, OptimizationActionCreate,
    VersionStatus, GradeConfig,
)


class MockNeo4jClient:
    def execute_query(self, query, parameters=None):
        if "螺栓连接" in str(parameters or {}):
            return [{"name": "螺栓连接"}]
        if "焊接" in str(parameters or {}):
            return [{"name": "焊接"}]
        return []


class MockLLMClient:
    def generate(self, prompt, **kwargs):
        return "该设计方案整体可拆卸性评价完成。"


@pytest.fixture
def system():
    return ClosedLoop(MockNeo4jClient(), MockLLMClient())


def _setup_version(system, subgraph, design_name="TestDesign"):
    """Create a version and override its subgraph with a custom one."""
    component_ids = [n["id"] for n in subgraph["nodes"] if "L1_Component" in n.get("labels", [])]
    connection_ids = [n["id"] for n in subgraph["nodes"] if "ConnectionType" in n.get("labels", [])]
    version = system.version_manager.create_version(DesignVersionCreate(
        design_name=design_name,
        component_ids=component_ids,
        connection_ids=connection_ids,
    ))
    system.version_manager._subgraphs[version.version_id] = subgraph
    return version


# -------------------------------------------------------------------
# 1. Full closed-loop with two versions: V1 welding (LOW) -> V2 bolt (better)
# -------------------------------------------------------------------

class TestFullClosedLoopTwoVersions:
    def test_full_closed_loop_two_versions(self, system):
        """V1 uses welding -> LOW grade -> create swap action -> apply -> V2 -> re-evaluate -> better score."""

        # -- Setup rules --
        weld_rule = system.rule_engine.create_rule(L4RuleCreate(
            name="焊接难拆规则",
            conclusion_score=0.3,
            conclusion_grade=Grade.UNQUALIFIED,
            weight=1.0,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="焊接连接"),
            ],
        ))
        bolt_rule = system.rule_engine.create_rule(L4RuleCreate(
            name="螺栓易拆规则",
            conclusion_score=0.8,
            conclusion_grade=Grade.GOOD,
            weight=1.0,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            ],
        ))

        # -- V1: uses welding connection --
        v1_subgraph = {
            "nodes": [
                {"id": "comp1", "labels": ["L1_Component"], "name": "电池外壳"},
                {"id": "weld_conn", "labels": ["ConnectionType"], "name": "焊接连接"},
            ],
            "relationships": [
                {"start": "comp1", "end": "weld_conn", "type": "USES_CONNECTION"},
            ],
        }
        v1 = _setup_version(system, v1_subgraph, design_name="电池方案")

        # -- Stage 1: Reason on V1 --
        assessment_v1 = system.reason(v1.version_id)
        # Weld rule matched (0.3*1.0 = 0.3), bolt rule not matched (0.0)
        # Score = 0.3 / 2.0 = 0.15 -> LOW
        assert assessment_v1.overall_score == pytest.approx(0.15, abs=0.01)
        assert assessment_v1.overall_grade == Grade.UNQUALIFIED

        matched_v1 = [m for m in assessment_v1.rule_matches if m.matched]
        unmatched_v1 = [m for m in assessment_v1.rule_matches if not m.matched]
        assert len(matched_v1) == 1
        assert len(unmatched_v1) == 1

        # -- Stage 2: Generate feedback --
        feedback_result = system.generate_feedback(assessment_v1.assessment_id)
        assert "summary" in feedback_result
        assert len(feedback_result["suggestions"]) >= 1  # bolt rule unmatched
        assert len(feedback_result["risks"]) >= 1  # LOW grade triggers high risk

        # -- Stage 3: Expert confirms (no score revision) --
        expert_fb = system.correct(
            assessment_v1.assessment_id,
            ExpertFeedbackCreate(
                feedback_type=FeedbackType.CONFIRM,
                original_score=0.15,
                expert_name="Dr. Zhang",
                comment="Score is accurate.",
            ),
        )
        assert expert_fb is not None
        assert expert_fb.feedback_type == FeedbackType.CONFIRM
        # Confirm should NOT revise score
        stored = system.get_assessment(assessment_v1.assessment_id)
        assert stored.status == AssessmentStatus.PENDING_REVIEW

        # -- Stage 4: Create swap action: welding -> bolt --
        action = system.action_executor.create_action(
            assessment_v1.assessment_id,
            OptimizationActionCreate(
                operation=ActionOperation.SWAP_CONNECTION,
                target_label="焊接连接",
                reason="Replace welding with bolt for easier disassembly",
                payload={
                    "remove_rel": {"start": "comp1", "end": "weld_conn", "type": "USES_CONNECTION"},
                    "add_rel": {"start": "comp1", "end": "bolt_conn", "type": "USES_CONNECTION"},
                },
            ),
        )
        # Also add the bolt_conn node
        add_node_action = system.action_executor.create_action(
            assessment_v1.assessment_id,
            OptimizationActionCreate(
                operation=ActionOperation.ADD_NODE,
                target_label="ConnectionType",
                payload={"id": "bolt_conn", "labels": ["ConnectionType"], "name": "螺栓连接"},
            ),
        )

        v2 = system.apply_and_new_version(
            v1.version_id, [action.action_id, add_node_action.action_id]
        )
        assert v2.version_id != v1.version_id
        assert v2.version_number > v1.version_number

        # Verify actions are marked APPLIED
        assert system.action_executor._actions[action.action_id].status == ActionStatus.APPLIED
        assert system.action_executor._actions[add_node_action.action_id].status == ActionStatus.APPLIED

        # -- Re-evaluate V2 --
        assessment_v2 = system.reason(v2.version_id)
        # Now bolt_rule matches (0.8*1.0 = 0.8), weld_rule does NOT match
        # Score = 0.8 / 2.0 = 0.4 -> MEDIUM
        assert assessment_v2.overall_score == pytest.approx(0.4, abs=0.01)
        assert assessment_v2.overall_grade == Grade.QUALIFIED
        assert assessment_v2.overall_score > assessment_v1.overall_score


# -------------------------------------------------------------------
# 2. Prediction from parameters (pseudo-subgraph from design params)
# -------------------------------------------------------------------

class TestPredictionFromParameters:
    def test_prediction_from_parameters(self, system):
        """Build a subgraph from design parameters and verify evaluation score."""

        system.rule_engine.create_rule(L4RuleCreate(
            name="标准工具可用规则",
            conclusion_score=0.85,
            conclusion_grade=Grade.GOOD,
            weight=1.0,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_TOOL", target_label="标准扳手"),
            ],
        ))
        system.rule_engine.create_rule(L4RuleCreate(
            name="螺栓连接可拆规则",
            conclusion_score=0.75,
            conclusion_grade=Grade.GOOD,
            weight=1.0,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            ],
        ))

        # Build a pseudo-subgraph simulating design parameters
        subgraph = {
            "nodes": [
                {"id": "battery_pack", "labels": ["L1_Component"], "name": "电池包"},
                {"id": "bolt_conn", "labels": ["ConnectionType"], "name": "螺栓连接"},
                {"id": "std_wrench", "labels": ["Tool"], "name": "标准扳手"},
            ],
            "relationships": [
                {"start": "battery_pack", "end": "bolt_conn", "type": "USES_CONNECTION"},
                {"start": "battery_pack", "end": "std_wrench", "type": "REQUIRES_TOOL"},
            ],
        }
        version = _setup_version(system, subgraph)
        assessment = system.reason(version.version_id)

        # Both rules matched: (0.85 + 0.75) / 2.0 = 0.8 -> EXCELLENT (>= 0.75)
        assert assessment.overall_score == pytest.approx(0.8, abs=0.01)
        assert assessment.overall_grade == Grade.EXCELLENT
        assert len([m for m in assessment.rule_matches if m.matched]) == 2


# -------------------------------------------------------------------
# 3. Multiple rules with different weights -> weighted average
# -------------------------------------------------------------------

class TestMultipleRulesWeighted:
    def test_multiple_rules_weighted(self, system):
        """Rules with different weights produce correct weighted average."""

        # Rule A: weight=2.0, score=0.9, always matches
        system.rule_engine.create_rule(L4RuleCreate(
            name="高权重规则",
            conclusion_score=0.9,
            conclusion_grade=Grade.GOOD,
            weight=2.0,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="卡扣连接"),
            ],
        ))
        # Rule B: weight=1.0, score=0.5, always matches
        system.rule_engine.create_rule(L4RuleCreate(
            name="中权重规则",
            conclusion_score=0.5,
            conclusion_grade=Grade.QUALIFIED,
            weight=1.0,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_TOOL", target_label="标准扳手"),
            ],
        ))
        # Rule C: weight=1.0, score=0.3, does NOT match
        system.rule_engine.create_rule(L4RuleCreate(
            name="低权重规则不匹配",
            conclusion_score=0.3,
            conclusion_grade=Grade.UNQUALIFIED,
            weight=1.0,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="焊接连接"),
            ],
        ))

        subgraph = {
            "nodes": [
                {"id": "c1", "labels": ["L1_Component"], "name": "模块"},
                {"id": "snap", "labels": ["ConnectionType"], "name": "卡扣连接"},
                {"id": "wrench", "labels": ["Tool"], "name": "标准扳手"},
            ],
            "relationships": [
                {"start": "c1", "end": "snap", "type": "USES_CONNECTION"},
                {"start": "c1", "end": "wrench", "type": "REQUIRES_TOOL"},
            ],
        }
        version = _setup_version(system, subgraph)
        assessment = system.reason(version.version_id)

        # Weighted: (0.9*2.0 + 0.5*1.0 + 0.0*1.0) / (2.0+1.0+1.0)
        # = (1.8 + 0.5 + 0) / 4.0 = 0.575 -> GOOD (0.55 <= 0.575 < 0.75)
        assert assessment.overall_score == pytest.approx(0.575, abs=0.01)
        assert assessment.overall_grade == Grade.GOOD

        matched = [m for m in assessment.rule_matches if m.matched]
        assert len(matched) == 2


# -------------------------------------------------------------------
# 4. Version comparison: diff two versions
# -------------------------------------------------------------------

class TestVersionComparison:
    def test_version_comparison(self, system):
        """Create V1 and V2 with different subgraphs, diff them, verify added/removed."""

        v1_subgraph = {
            "nodes": [
                {"id": "n1", "labels": ["L1_Component"], "name": "电池外壳"},
                {"id": "n2", "labels": ["ConnectionType"], "name": "螺栓连接"},
            ],
            "relationships": [
                {"start": "n1", "end": "n2", "type": "USES_CONNECTION"},
            ],
        }
        v2_subgraph = {
            "nodes": [
                {"id": "n1", "labels": ["L1_Component"], "name": "电池外壳"},
                {"id": "n3", "labels": ["ConnectionType"], "name": "卡扣连接"},
            ],
            "relationships": [
                {"start": "n1", "end": "n3", "type": "USES_CONNECTION"},
            ],
        }
        v1 = _setup_version(system, v1_subgraph, design_name="电池方案")
        v2 = _setup_version(system, v2_subgraph, design_name="电池方案")

        diff = system.version_manager.diff_versions(v1.version_id, v2.version_id)

        added_ids = [n["id"] for n in diff["added"]["nodes"]]
        removed_ids = [n["id"] for n in diff["removed"]["nodes"]]
        assert "n3" in added_ids
        assert "n2" in removed_ids

        added_rels = {(r["start"], r["end"], r["type"]) for r in diff["added"]["relationships"]}
        removed_rels = {(r["start"], r["end"], r["type"]) for r in diff["removed"]["relationships"]}
        assert ("n1", "n3", "USES_CONNECTION") in added_rels
        assert ("n1", "n2", "USES_CONNECTION") in removed_rels


# -------------------------------------------------------------------
# 5. Action chain: multiple actions applied sequentially
# -------------------------------------------------------------------

class TestActionChain:
    def test_action_chain(self, system):
        """Create multiple actions, apply_actions sequentially, verify cumulative effect."""

        subgraph = {
            "nodes": [
                {"id": "c1", "labels": ["L1_Component"], "name": "电池外壳"},
            ],
            "relationships": [],
        }
        version = _setup_version(system, subgraph)
        assessment = system.reason(version.version_id)

        # Action 1: Add a bolt connection node
        a1 = system.action_executor.create_action(
            assessment.assessment_id,
            OptimizationActionCreate(
                operation=ActionOperation.ADD_NODE,
                target_label="ConnectionType",
                payload={"id": "bolt", "labels": ["ConnectionType"], "name": "螺栓连接"},
            ),
        )
        # Action 2: Add a relationship from c1 to bolt
        a2 = system.action_executor.create_action(
            assessment.assessment_id,
            OptimizationActionCreate(
                operation=ActionOperation.ADD_REL,
                payload={"start": "c1", "end": "bolt", "type": "USES_CONNECTION"},
            ),
        )
        # Action 3: Modify a property on c1
        a3 = system.action_executor.create_action(
            assessment.assessment_id,
            OptimizationActionCreate(
                operation=ActionOperation.MODIFY_PROPERTY,
                target_id="c1",
                payload={"property": "removable", "new_value": True},
            ),
        )

        # Apply all actions in sequence
        result_subgraph = system.action_executor.apply_actions(
            subgraph, [a1, a2, a3]
        )

        # Verify cumulative effect
        node_ids = [n["id"] for n in result_subgraph["nodes"]]
        assert "bolt" in node_ids

        rels = result_subgraph["relationships"]
        assert any(r["start"] == "c1" and r["end"] == "bolt" for r in rels)

        c1_node = next(n for n in result_subgraph["nodes"] if n["id"] == "c1")
        assert c1_node["removable"] is True

        # Verify count: original 1 node + 1 added = 2 nodes
        assert len(result_subgraph["nodes"]) == 2
        assert len(result_subgraph["relationships"]) == 1


# -------------------------------------------------------------------
# 6. Feedback roundtrip: reason -> generate_feedback -> correct with revise
# -------------------------------------------------------------------

class TestFeedbackRoundtrip:
    def test_feedback_roundtrip(self, system):
        """reason -> generate_feedback -> correct with revise -> verify score updated."""

        system.rule_engine.create_rule(L4RuleCreate(
            name="螺栓易拆规则",
            conclusion_score=0.8,
            conclusion_grade=Grade.GOOD,
            weight=1.0,
            conditions=[
                L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
            ],
        ))

        subgraph = {
            "nodes": [
                {"id": "n1", "labels": ["L1_Component"], "name": "电池外壳"},
                {"id": "n2", "labels": ["ConnectionType"], "name": "焊接连接"},  # does NOT match
            ],
            "relationships": [
                {"start": "n1", "end": "n2", "type": "USES_CONNECTION"},
            ],
        }
        version = _setup_version(system, subgraph)

        # Stage 1: Reason
        assessment = system.reason(version.version_id)
        # Bolt rule does NOT match -> score = 0.0 -> LOW
        assert assessment.overall_score == pytest.approx(0.0, abs=0.01)
        assert assessment.overall_grade == Grade.UNQUALIFIED

        # Stage 2: Generate feedback
        feedback_result = system.generate_feedback(assessment.assessment_id)
        assert "summary" in feedback_result
        assert len(feedback_result["suggestions"]) == 1  # bolt rule unmatched
        assert len(feedback_result["risks"]) >= 1  # LOW grade -> high risk

        # Stage 3: Expert revises score
        expert_fb = system.correct(
            assessment.assessment_id,
            ExpertFeedbackCreate(
                feedback_type=FeedbackType.REVISE,
                original_score=0.0,
                revised_score=0.45,
                expert_name="Dr. Wang",
                comment="焊接虽难拆但实际可操作，分数应适当上调。",
            ),
        )
        assert expert_fb is not None
        assert expert_fb.feedback_type == FeedbackType.REVISE
        assert expert_fb.revised_score == 0.45

        # Verify score is updated
        stored = system.get_assessment(assessment.assessment_id)
        assert stored.overall_score == 0.45
        assert stored.overall_grade == Grade.QUALIFIED
        assert stored.status == AssessmentStatus.REVISED

        # Verify feedback is retrievable
        feedbacks = system.get_feedbacks(assessment.assessment_id)
        assert len(feedbacks) == 1
        assert feedbacks[0].expert_name == "Dr. Wang"


# -------------------------------------------------------------------
# 7. Multi-dimensional evaluation: rules in different dimensions -> dimension_scores
# -------------------------------------------------------------------

class TestMultiDimensionalEvaluation:
    def test_dimension_scores_in_assessment(self, system):
        """Rules in different dimensions produce dimension_scores."""
        system.rule_engine.create_rule(L4RuleCreate(
            name="螺栓易拆",
            conclusion_score=0.85,
            conclusion_grade=Grade.GOOD,
            dimension="technical",
            weight=1.0,
            conditions=[L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接")],
        ))
        system.rule_engine.create_rule(L4RuleCreate(
            name="回收价值高",
            conclusion_score=0.7,
            conclusion_grade=Grade.GOOD,
            dimension="economic",
            weight=1.0,
            conditions=[L4RuleCondition(condition_type="REQUIRES_TOOL", target_label="标准扳手")],
        ))
        system.rule_engine.create_rule(L4RuleCreate(
            name="废料少",
            conclusion_score=0.6,
            conclusion_grade=Grade.QUALIFIED,
            dimension="environmental",
            weight=1.0,
            conditions=[L4RuleCondition(condition_type="REQUIRES_STRUCTURE", target_label="模块化设计")],
        ))

        subgraph = {
            "nodes": [
                {"id": "c1", "labels": ["L1_Component"], "name": "电池外壳"},
                {"id": "bolt", "labels": ["ConnectionType"], "name": "螺栓连接"},
                {"id": "wrench", "labels": ["Tool"], "name": "标准扳手"},
                {"id": "modular", "labels": ["StructureFeature"], "name": "模块化设计"},
            ],
            "relationships": [
                {"start": "c1", "end": "bolt", "type": "USES_CONNECTION"},
                {"start": "c1", "end": "wrench", "type": "REQUIRES_TOOL"},
                {"start": "c1", "end": "modular", "type": "HAS_FEATURE"},
            ],
        }
        version = _setup_version(system, subgraph)
        assessment = system.reason(version.version_id)

        # Verify dimension scores exist
        assert len(assessment.dimension_scores) == 3
        assert assessment.evaluation_mode == "single"

        # Find each dimension
        tech = next(d for d in assessment.dimension_scores if d.dimension == "technical")
        econ = next(d for d in assessment.dimension_scores if d.dimension == "economic")
        env = next(d for d in assessment.dimension_scores if d.dimension == "environmental")

        assert tech.score == pytest.approx(0.85, abs=0.01)
        assert econ.score == pytest.approx(0.7, abs=0.01)
        assert env.score == pytest.approx(0.6, abs=0.01)
        assert tech.matched_rules == 1
        assert econ.matched_rules == 1
        assert env.matched_rules == 1


# -------------------------------------------------------------------
# 8. Batch assessment with RSR
# -------------------------------------------------------------------

class TestBatchAssessment:
    def test_batch_assess_two_versions(self, system):
        """Batch assessment of two versions produces RSR-based results."""
        system.rule_engine.create_rule(L4RuleCreate(
            name="螺栓易拆",
            conclusion_score=0.8,
            conclusion_grade=Grade.GOOD,
            dimension="technical",
            weight=1.0,
            conditions=[L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接")],
        ))

        sg_bolt = {
            "nodes": [
                {"id": "c1", "labels": ["L1_Component"], "name": "电池外壳"},
                {"id": "bolt", "labels": ["ConnectionType"], "name": "螺栓连接"},
            ],
            "relationships": [{"start": "c1", "end": "bolt", "type": "USES_CONNECTION"}],
        }
        sg_weld = {
            "nodes": [
                {"id": "c1", "labels": ["L1_Component"], "name": "电池外壳"},
                {"id": "weld", "labels": ["ConnectionType"], "name": "焊接连接"},
            ],
            "relationships": [{"start": "c1", "end": "weld", "type": "USES_CONNECTION"}],
        }

        v1 = _setup_version(system, sg_bolt, design_name="方案A")
        v2 = _setup_version(system, sg_weld, design_name="方案B")

        assessments = system.batch_assess([v1.version_id, v2.version_id])

        assert len(assessments) == 2
        for a in assessments:
            assert a.evaluation_mode == "batch"
            assert a.grade_thresholds is not None
            assert len(a.dimension_scores) == 3
            for ds in a.dimension_scores:
                assert ds.rsr_value is not None
                assert ds.rank is not None

        # Bolt version should have higher technical RSR and better technical rank
        bolt_a = next(a for a in assessments if a.version_id == v1.version_id)
        weld_a = next(a for a in assessments if a.version_id == v2.version_id)

        bolt_tech = next(d for d in bolt_a.dimension_scores if d.dimension == "technical")
        weld_tech = next(d for d in weld_a.dimension_scores if d.dimension == "technical")
        assert bolt_tech.rsr_value > weld_tech.rsr_value
        assert bolt_tech.rank < weld_tech.rank
        assert bolt_tech.matched_rules == 1
        assert weld_tech.matched_rules == 0

    def test_batch_assess_empty_versions_raises(self, system):
        """batch_assess with non-existent version raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            system.batch_assess(["nonexistent_v1"])


# -------------------------------------------------------------------
# 9. Grade config: get, update, calibrate
# -------------------------------------------------------------------

class TestGradeConfig:
    def test_get_default_grade_config(self, system):
        """Default grade config has expected thresholds."""
        config = system.get_grade_config()
        assert config.excellent_threshold == 0.75
        assert config.good_threshold == 0.55
        assert config.qualified_threshold == 0.35
        assert config.source == "default"

    def test_update_grade_config(self, system):
        """Update grade config persists changes."""
        new_config = GradeConfig(
            excellent_threshold=0.8,
            good_threshold=0.6,
            qualified_threshold=0.4,
            source="manual",
        )
        result = system.update_grade_config(new_config)
        assert result.excellent_threshold == 0.8
        assert result.source == "manual"

        # Verify it persists
        stored = system.get_grade_config()
        assert stored.excellent_threshold == 0.8

    def test_calibrate_thresholds_needs_10_assessments(self, system):
        """Calibration fails with fewer than 10 assessments."""
        with pytest.raises(ValueError, match="不足"):
            system.calibrate_thresholds()


# -------------------------------------------------------------------
# 10. End-to-end: create rule with dimension -> assess -> verify
# -------------------------------------------------------------------

class TestEndToEndDimensionEvaluation:
    def test_create_dimension_rule_and_evaluate(self, system):
        """Full flow: create rule with dimension -> create version -> evaluate -> check dimension scores."""
        # Create rules in 3 dimensions
        for dim, name, score, label in [
            ("technical", "技术规则", 0.8, "螺栓连接"),
            ("economic", "经济规则", 0.6, "标准扳手"),
            ("environmental", "环境规则", 0.5, "模块化设计"),
        ]:
            system.rule_engine.create_rule(L4RuleCreate(
                name=name,
                conclusion_score=score,
                conclusion_grade=Grade.GOOD,
                dimension=dim,
                weight=1.0,
                conditions=[L4RuleCondition(
                    condition_type="REQUIRES_CONNECTION" if dim == "technical" else "REQUIRES_TOOL" if dim == "economic" else "REQUIRES_STRUCTURE",
                    target_label=label,
                )],
            ))

        subgraph = {
            "nodes": [
                {"id": "c1", "labels": ["L1_Component"], "name": "电池外壳"},
                {"id": "bolt", "labels": ["ConnectionType"], "name": "螺栓连接"},
                {"id": "wrench", "labels": ["Tool"], "name": "标准扳手"},
                {"id": "modular", "labels": ["StructureFeature"], "name": "模块化设计"},
            ],
            "relationships": [
                {"start": "c1", "end": "bolt", "type": "USES_CONNECTION"},
                {"start": "c1", "end": "wrench", "type": "REQUIRES_TOOL"},
                {"start": "c1", "end": "modular", "type": "HAS_FEATURE"},
            ],
        }
        version = _setup_version(system, subgraph)
        assessment = system.reason(version.version_id)

        # Verify all 3 dimensions present
        dims = {d.dimension: d for d in assessment.dimension_scores}
        assert "technical" in dims
        assert "economic" in dims
        assert "environmental" in dims

        assert dims["technical"].score == pytest.approx(0.8, abs=0.01)
        assert dims["economic"].score == pytest.approx(0.6, abs=0.01)
        assert dims["environmental"].score == pytest.approx(0.5, abs=0.01)

        # Overall should be weighted average of dimension scores
        # (0.8*1.0 + 0.6*1.0 + 0.5*1.0) / 3.0 = 0.633
        assert assessment.overall_score == pytest.approx(0.633, abs=0.02)
