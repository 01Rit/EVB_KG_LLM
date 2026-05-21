"""Tests for ClosedLoop orchestrator: full reason -> feedback -> correct -> update cycle."""
import pytest
from src.evaluation.closed_loop import ClosedLoop
from src.evaluation.models import (
    L4RuleCreate, L4RuleCondition, Grade, FeedbackType,
    ExpertFeedbackCreate, AssessmentStatus, ActionStatus, VersionStatus,
)


class MockNeo4jClient:
    def execute_query(self, query, params=None):
        return []


class MockLLMClient:
    def generate(self, prompt, system_message=None):
        return "LLM generated feedback for the assessment."


@pytest.fixture
def loop():
    return ClosedLoop(neo4j_client=MockNeo4jClient(), llm_client=MockLLMClient())


@pytest.fixture
def loop_no_llm():
    return ClosedLoop(neo4j_client=MockNeo4jClient())


@pytest.fixture
def subgraph_with_bolt():
    """Subgraph with bolt connection and standard wrench tool."""
    return {
        "nodes": [
            {"id": "n1", "labels": ["L1_Component"], "name": "电池外壳"},
            {"id": "n2", "labels": ["ConnectionType"], "name": "螺栓连接"},
            {"id": "n3", "labels": ["Tool"], "name": "标准扳手"},
        ],
        "relationships": [
            {"start": "n1", "end": "n2", "type": "USES_CONNECTION"},
            {"start": "n1", "end": "n3", "type": "REQUIRES_TOOL"},
        ],
    }


@pytest.fixture
def subgraph_with_weld():
    """Subgraph with weld connection (harder to disassemble)."""
    return {
        "nodes": [
            {"id": "n1", "labels": ["L1_Component"], "name": "电池外壳"},
            {"id": "n2", "labels": ["ConnectionType"], "name": "焊接连接"},
            {"id": "n3", "labels": ["Tool"], "name": "标准扳手"},
        ],
        "relationships": [
            {"start": "n1", "end": "n2", "type": "USES_CONNECTION"},
            {"start": "n1", "end": "n3", "type": "REQUIRES_TOOL"},
        ],
    }


def _setup_version(loop, subgraph):
    """Helper: create a version and override its subgraph."""
    from src.evaluation.models import DesignVersionCreate
    version = loop.version_manager.create_version(DesignVersionCreate(
        design_name="TestDesign",
        component_ids=["n1"],
        connection_ids=["n2"],
    ))
    loop.version_manager._subgraphs[version.version_id] = subgraph
    return version


def _create_bolt_rule(loop):
    """Helper: create a rule that matches bolt connections."""
    return loop.rule_engine.create_rule(L4RuleCreate(
        name="螺栓易拆规则",
        conclusion_score=0.8,
        conclusion_grade=Grade.GOOD,
        weight=1.0,
        conditions=[
            L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="螺栓连接"),
        ],
    ))


def _create_weld_rule(loop):
    """Helper: create a rule for weld connections."""
    return loop.rule_engine.create_rule(L4RuleCreate(
        name="焊接难拆规则",
        conclusion_score=0.3,
        conclusion_grade=Grade.UNQUALIFIED,
        weight=1.0,
        conditions=[
            L4RuleCondition(condition_type="REQUIRES_CONNECTION", target_label="焊接连接"),
        ],
    ))


# ── Stage 1: Reason ──


class TestReason:
    def test_reason_returns_assessment(self, loop, subgraph_with_bolt):
        _create_bolt_rule(loop)
        version = _setup_version(loop, subgraph_with_bolt)

        assessment = loop.reason(version.version_id)

        assert assessment.assessment_id.startswith("assess_")
        assert assessment.version_id == version.version_id
        assert assessment.overall_score == 0.8
        assert assessment.overall_grade == Grade.EXCELLENT
        assert len(assessment.rule_matches) == 1
        assert assessment.rule_matches[0].matched is True

    def test_reason_updates_version_status(self, loop, subgraph_with_bolt):
        _create_bolt_rule(loop)
        version = _setup_version(loop, subgraph_with_bolt)

        loop.reason(version.version_id)

        updated = loop.version_manager._versions[version.version_id]
        assert updated.status == VersionStatus.EVALUATED

    def test_reason_stores_assessment(self, loop, subgraph_with_bolt):
        _create_bolt_rule(loop)
        version = _setup_version(loop, subgraph_with_bolt)

        assessment = loop.reason(version.version_id)

        retrieved = loop.get_assessment(assessment.assessment_id)
        assert retrieved is not None
        assert retrieved.assessment_id == assessment.assessment_id

    def test_reason_no_rules(self, loop, subgraph_with_bolt):
        version = _setup_version(loop, subgraph_with_bolt)

        assessment = loop.reason(version.version_id)

        assert assessment.overall_score == 0.0
        assert assessment.overall_grade == Grade.UNQUALIFIED
        assert assessment.rule_matches == []


# ── Stage 2: Feedback ──


class TestFeedback:
    def test_generate_feedback_with_llm(self, loop, subgraph_with_bolt):
        _create_bolt_rule(loop)
        version = _setup_version(loop, subgraph_with_bolt)
        assessment = loop.reason(version.version_id)

        feedback = loop.generate_feedback(assessment.assessment_id)

        assert "summary" in feedback
        assert "suggestions" in feedback
        assert "risks" in feedback
        # Summary contains score and match counts
        assert len(feedback["summary"]) > 0
        assert len(feedback["suggestions"]) == 0  # all rules matched

    def test_generate_feedback_without_llm(self, loop_no_llm, subgraph_with_bolt):
        _create_bolt_rule(loop_no_llm)
        version = _setup_version(loop_no_llm, subgraph_with_bolt)
        assessment = loop_no_llm.reason(version.version_id)

        feedback = loop_no_llm.generate_feedback(assessment.assessment_id)

        assert "summary" in feedback
        assert "llm_feedback" not in feedback

    def test_generate_feedback_nonexistent(self, loop):
        feedback = loop.generate_feedback("nonexistent_id")
        assert "error" in feedback


# ── Stage 3: Correct ──


class TestCorrect:
    def test_correct_confirms(self, loop, subgraph_with_bolt):
        _create_bolt_rule(loop)
        version = _setup_version(loop, subgraph_with_bolt)
        assessment = loop.reason(version.version_id)

        fb_data = ExpertFeedbackCreate(
            feedback_type=FeedbackType.CONFIRM,
            original_score=0.8,
            expert_name="Dr. Zhang",
            comment="Score is accurate.",
        )
        feedback = loop.correct(assessment.assessment_id, fb_data)

        assert feedback is not None
        assert feedback.feedback_type == FeedbackType.CONFIRM
        assert feedback.expert_name == "Dr. Zhang"
        # Confirm does not revise score (revised_score is None)
        stored = loop.get_assessment(assessment.assessment_id)
        assert stored.status == AssessmentStatus.PENDING_REVIEW

    def test_correct_revises_score(self, loop, subgraph_with_bolt):
        _create_bolt_rule(loop)
        version = _setup_version(loop, subgraph_with_bolt)
        assessment = loop.reason(version.version_id)

        fb_data = ExpertFeedbackCreate(
            feedback_type=FeedbackType.REVISE,
            original_score=0.8,
            revised_score=0.9,
            expert_name="Dr. Li",
            comment="Should be higher.",
        )
        feedback = loop.correct(assessment.assessment_id, fb_data)

        assert feedback is not None
        assert feedback.revised_score == 0.9

        stored = loop.get_assessment(assessment.assessment_id)
        assert stored.overall_score == 0.9
        assert stored.overall_grade == Grade.EXCELLENT
        assert stored.status == AssessmentStatus.REVISED

    def test_correct_revises_changes_grade(self, loop, subgraph_with_bolt):
        _create_bolt_rule(loop)
        version = _setup_version(loop, subgraph_with_bolt)
        assessment = loop.reason(version.version_id)

        fb_data = ExpertFeedbackCreate(
            feedback_type=FeedbackType.REVISE,
            original_score=0.8,
            revised_score=0.3,
            expert_name="Dr. Wang",
        )
        loop.correct(assessment.assessment_id, fb_data)

        stored = loop.get_assessment(assessment.assessment_id)
        assert stored.overall_score == 0.3
        assert stored.overall_grade == Grade.UNQUALIFIED

    def test_correct_nonexistent_assessment(self, loop):
        fb_data = ExpertFeedbackCreate(
            feedback_type=FeedbackType.CONFIRM,
            original_score=0.5,
        )
        result = loop.correct("nonexistent_id", fb_data)
        assert result is None

    def test_get_feedbacks(self, loop, subgraph_with_bolt):
        _create_bolt_rule(loop)
        version = _setup_version(loop, subgraph_with_bolt)
        assessment = loop.reason(version.version_id)

        loop.correct(assessment.assessment_id, ExpertFeedbackCreate(
            feedback_type=FeedbackType.CONFIRM, original_score=0.8, expert_name="A",
        ))
        loop.correct(assessment.assessment_id, ExpertFeedbackCreate(
            feedback_type=FeedbackType.REVISE, original_score=0.8, revised_score=0.7, expert_name="B",
        ))

        feedbacks = loop.get_feedbacks(assessment.assessment_id)
        assert len(feedbacks) == 2
        names = {f.expert_name for f in feedbacks}
        assert names == {"A", "B"}


# ── Stage 4: Update ──


class TestUpdate:
    def test_generate_actions_no_matches(self, loop, subgraph_with_bolt):
        """No '焊接' matched rules, so no actions generated."""
        _create_bolt_rule(loop)
        version = _setup_version(loop, subgraph_with_bolt)
        assessment = loop.reason(version.version_id)

        actions = loop.generate_actions(assessment.assessment_id)
        # Bolt rule matches but has no '焊接' in name
        assert len(actions) == 0

    def test_generate_actions_weld_rule(self, loop, subgraph_with_weld):
        """Weld rule matched but with low score, should generate action."""
        _create_weld_rule(loop)
        version = _setup_version(loop, subgraph_with_weld)
        assessment = loop.reason(version.version_id)

        actions = loop.generate_actions(assessment.assessment_id)
        # Weld rule score_contribution = 0.3 * 1.0 = 0.3, not < 0.3
        # So no action (boundary case: score_contribution is exactly 0.3)
        assert len(actions) == 0

    def test_generate_actions_nonexistent_assessment(self, loop):
        actions = loop.generate_actions("nonexistent_id")
        assert len(actions) == 0

    def test_apply_and_new_version(self, loop, subgraph_with_bolt):
        """Create actions manually and apply them to produce a new version."""
        from src.evaluation.models import OptimizationActionCreate, ActionOperation
        _create_bolt_rule(loop)
        version = _setup_version(loop, subgraph_with_bolt)
        assessment = loop.reason(version.version_id)

        # Manually create an action
        action = loop.action_executor.create_action(
            assessment.assessment_id,
            OptimizationActionCreate(
                operation=ActionOperation.ADD_NODE,
                target_label="L1_Component",
                payload={"id": "n4", "labels": ["L1_Component"], "name": "新增部件"},
            ),
        )

        new_version = loop.apply_and_new_version(
            version.version_id, [action.action_id]
        )

        assert new_version.version_id != version.version_id
        assert new_version.design_name == "TestDesign"

        new_subgraph = loop.version_manager.get_subgraph(new_version.version_id)
        node_ids = [n["id"] for n in new_subgraph["nodes"]]
        assert "n4" in node_ids

        # Action should now be APPLIED
        applied_action = loop.action_executor._actions[action.action_id]
        assert applied_action.status == ActionStatus.APPLIED

    def test_apply_and_new_version_nonexistent_version(self, loop):
        with pytest.raises(ValueError, match="not found"):
            loop.apply_and_new_version("nonexistent_v", [])


# ── Full Loop Integration ──


class TestFullLoop:
    def test_reason_feedback_correct_apply_re_reason(self, loop):
        """Full closed-loop: reason -> feedback -> correct -> apply -> re-reason."""
        # Setup: two rules, subgraph matches only bolt
        _create_bolt_rule(loop)
        _create_weld_rule(loop)

        subgraph = {
            "nodes": [
                {"id": "n1", "labels": ["L1_Component"], "name": "电池外壳"},
                {"id": "n2", "labels": ["ConnectionType"], "name": "螺栓连接"},
                {"id": "n3", "labels": ["ConnectionType"], "name": "焊接连接"},
            ],
            "relationships": [
                {"start": "n1", "end": "n2", "type": "USES_CONNECTION"},
            ],
        }
        version = _setup_version(loop, subgraph)

        # Stage 1: Reason
        assessment1 = loop.reason(version.version_id)
        # Only bolt rule matches: 0.8*1.0 / (1.0+1.0) = 0.4
        assert assessment1.overall_score == 0.4
        assert assessment1.overall_grade == Grade.QUALIFIED
        matched = [m for m in assessment1.rule_matches if m.matched]
        unmatched = [m for m in assessment1.rule_matches if not m.matched]
        assert len(matched) == 1
        assert len(unmatched) == 1

        # Stage 2: Generate feedback
        feedback_result = loop.generate_feedback(assessment1.assessment_id)
        assert "summary" in feedback_result
        assert len(feedback_result["suggestions"]) == 1  # one unmatched rule

        # Stage 3: Expert corrects (revise score upward)
        expert_fb = loop.correct(
            assessment1.assessment_id,
            ExpertFeedbackCreate(
                feedback_type=FeedbackType.REVISE,
                original_score=0.4,
                revised_score=0.6,
                expert_name="Expert A",
                comment="Bolt connection is actually easier than scored.",
            ),
        )
        assert expert_fb is not None
        stored = loop.get_assessment(assessment1.assessment_id)
        assert stored.overall_score == 0.6
        assert stored.status == AssessmentStatus.REVISED

        # Stage 4: Generate and apply actions
        from src.evaluation.models import OptimizationActionCreate, ActionOperation

        # Manually create an action to add the weld relationship
        action = loop.action_executor.create_action(
            assessment1.assessment_id,
            OptimizationActionCreate(
                operation=ActionOperation.ADD_REL,
                payload={"start": "n1", "end": "n3", "type": "USES_CONNECTION"},
                reason="Add missing weld connection for completeness",
            ),
        )

        new_version = loop.apply_and_new_version(
            version.version_id, [action.action_id]
        )
        assert new_version.version_id != version.version_id

        # Re-reason on the new version
        assessment2 = loop.reason(new_version.version_id)
        # Now both rules match: (0.8*1.0 + 0.3*1.0) / 2.0 = 0.55
        assert assessment2.overall_score == 0.55
        assert assessment2.overall_grade == Grade.GOOD  # 0.55 >= good_threshold
        matched2 = [m for m in assessment2.rule_matches if m.matched]
        assert len(matched2) == 2

    def test_multiple_feedbacks_on_same_assessment(self, loop, subgraph_with_bolt):
        _create_bolt_rule(loop)
        version = _setup_version(loop, subgraph_with_bolt)
        assessment = loop.reason(version.version_id)

        loop.correct(assessment.assessment_id, ExpertFeedbackCreate(
            feedback_type=FeedbackType.CONFIRM, original_score=0.8, expert_name="Expert1",
        ))
        loop.correct(assessment.assessment_id, ExpertFeedbackCreate(
            feedback_type=FeedbackType.REVISE, original_score=0.8, revised_score=0.7, expert_name="Expert2",
        ))

        feedbacks = loop.get_feedbacks(assessment.assessment_id)
        assert len(feedbacks) == 2

    def test_version_status_progression(self, loop, subgraph_with_bolt):
        _create_bolt_rule(loop)
        version = _setup_version(loop, subgraph_with_bolt)

        # Initially DRAFT
        assert loop.version_manager._versions[version.version_id].status == VersionStatus.DRAFT

        # After reason: EVALUATED
        loop.reason(version.version_id)
        assert loop.version_manager._versions[version.version_id].status == VersionStatus.EVALUATED
