"""Closed-loop orchestrator: reason -> feedback -> correct -> update."""
import logging
import uuid
from typing import Optional

import numpy as np

from src.evaluation.models import (
    L4Assessment, ReasoningPath, ExpertFeedback, ExpertFeedbackCreate,
    OptimizationAction, OptimizationActionCreate, DesignVersion,
    DesignVersionCreate, ActionOperation, ActionStatus, VersionStatus,
    AssessmentStatus, FeedbackType, Grade, RuleMatchDetail,
    GradeConfig, GradeThreshold,
)
from src.evaluation.rule_engine import RuleEngine
from src.evaluation.evaluator import Evaluator
from src.evaluation.version_manager import VersionManager
from src.evaluation.action_executor import ActionExecutor
from src.evaluation.feedback_generator import FeedbackGenerator

logger = logging.getLogger(__name__)


class ClosedLoop:
    """Orchestrates the 4-stage closed-loop:
    Reason -> Feedback -> Correct -> Update
    """

    def __init__(self, neo4j_client, llm_client=None):
        self.rule_engine = RuleEngine(neo4j_client)
        self.evaluator = Evaluator(self.rule_engine)
        self.version_manager = VersionManager(neo4j_client)
        self.action_executor = ActionExecutor()
        self.feedback_generator = FeedbackGenerator(llm_client)
        self._assessments: dict[str, L4Assessment] = {}
        self._feedbacks: dict[str, ExpertFeedback] = {}
        self._grade_config = GradeConfig()

    # -- Stage 1: Reason --

    def reason(self, version_id: str) -> L4Assessment:
        """Evaluate a design version against active rules."""
        subgraph = self.version_manager.get_subgraph(version_id)
        assessment = self.evaluator.evaluate(version_id, subgraph)
        self._assessments[assessment.assessment_id] = assessment
        self.version_manager.update_version_status(version_id, VersionStatus.EVALUATED)
        logger.info(
            f"Assessment {assessment.assessment_id}: "
            f"score={assessment.overall_score:.2f}, grade={assessment.overall_grade.value}"
        )
        return assessment

    # -- Stage 2: Feedback --

    def generate_feedback(self, assessment_id: str) -> dict:
        """Generate structured feedback for an assessment."""
        assessment = self._assessments.get(assessment_id)
        if not assessment:
            return {"error": "Assessment not found"}
        active_rules = self.rule_engine.get_rules()
        return self.feedback_generator.generate(assessment, active_rules)

    # -- Stage 3: Correct --

    def correct(self, assessment_id: str, feedback_data: ExpertFeedbackCreate) -> Optional[ExpertFeedback]:
        """Submit expert feedback and optionally revise the assessment score."""
        assessment = self._assessments.get(assessment_id)
        if not assessment:
            return None

        feedback_id = f"fb_{uuid.uuid4().hex[:8]}"
        feedback = ExpertFeedback(
            feedback_id=feedback_id,
            assessment_id=assessment_id,
            feedback_type=feedback_data.feedback_type,
            original_score=feedback_data.original_score,
            revised_score=feedback_data.revised_score,
            comment=feedback_data.comment,
            expert_name=feedback_data.expert_name,
        )
        self._feedbacks[feedback_id] = feedback

        if feedback_data.revised_score is not None:
            updated = assessment.model_copy(update={
                "overall_score": feedback_data.revised_score,
                "overall_grade": self.evaluator._score_to_grade(feedback_data.revised_score),
                "status": AssessmentStatus.REVISED,
            })
            self._assessments[assessment_id] = updated

        logger.info(f"Expert feedback {feedback_id}: {feedback_data.feedback_type.value}")
        return feedback

    # -- Stage 4: Update --

    def generate_actions(self, assessment_id: str) -> list[OptimizationAction]:
        """Generate optimization actions for unmatched or low-scoring rules."""
        assessment = self._assessments.get(assessment_id)
        if not assessment:
            return []

        actions = []
        for match in assessment.rule_matches:
            if not match.matched:
                continue
            if "焊接" in match.rule_name and match.score_contribution < 0.3:
                action = self.action_executor.create_action(
                    assessment_id,
                    OptimizationActionCreate(
                        operation=ActionOperation.SWAP_CONNECTION,
                        target_label="焊接连接",
                        reason=f"Rule '{match.rule_name}' has low score, suggest replacing with bolt connection",
                        payload={
                            "remove_rel": {"type": "USES_CONNECTION"},
                            "add_rel": {"type": "USES_CONNECTION", "end": "bolt_conn"},
                        },
                    )
                )
                actions.append(action)

        return actions

    def apply_and_new_version(self, current_version_id: str, action_ids: list[str]) -> DesignVersion:
        """Apply selected actions and create a new design version."""
        current = self.version_manager.get_version_detail(current_version_id)
        if not current:
            raise ValueError(f"Version {current_version_id} not found")

        subgraph = self.version_manager.get_subgraph(current_version_id)

        all_actions = []
        for aid in action_ids:
            action = self.action_executor._actions.get(aid)
            if action:
                all_actions.append(action)

        new_subgraph = self.action_executor.apply_actions(subgraph, all_actions)

        for action in all_actions:
            self.action_executor.mark_applied(action.action_id)

        component_ids = [
            n["id"] for n in new_subgraph["nodes"]
            if "L1_Component" in n.get("labels", [])
        ]
        connection_ids = [
            n["id"] for n in new_subgraph["nodes"]
            if "ConnectionType" in n.get("labels", [])
        ]

        new_version = self.version_manager.create_version(DesignVersionCreate(
            design_name=current.design_name,
            component_ids=component_ids,
            connection_ids=connection_ids,
        ))

        # Override the auto-built subgraph with our computed one
        self.version_manager._subgraphs[new_version.version_id] = new_subgraph

        logger.info(
            f"Created new version {new_version.version_id} from {current_version_id} "
            f"with {len(all_actions)} actions"
        )
        return new_version

    # -- Batch Assessment --

    def batch_assess(self, version_ids: list[str]) -> list[L4Assessment]:
        """Evaluate multiple versions using RSR method."""
        subgraphs = {}
        for vid in version_ids:
            sg = self.version_manager.get_subgraph(vid)
            if not sg or not sg.get("nodes"):
                raise ValueError(f"Version {vid} not found or has no data")
            subgraphs[vid] = sg
        assessments = self.evaluator.batch_evaluate(subgraphs)
        for a in assessments:
            self._assessments[a.assessment_id] = a
        return assessments

    # -- Grade Config --

    def get_grade_config(self) -> GradeConfig:
        return self._grade_config

    def update_grade_config(self, config: GradeConfig) -> GradeConfig:
        self._grade_config = config
        # Also update the evaluator's config
        self.evaluator.grade_config = config
        return config

    def calibrate_thresholds(self) -> GradeConfig:
        if len(self._assessments) < 10:
            raise ValueError("历史评价数据不足 10 条，无法标定")
        scores = [a.overall_score for a in self._assessments.values()]
        config = GradeConfig(
            excellent_threshold=float(np.percentile(scores, 75)),
            good_threshold=float(np.percentile(scores, 50)),
            qualified_threshold=float(np.percentile(scores, 25)),
            source="calibrated",
        )
        self._grade_config = config
        self.evaluator.grade_config = config
        return config

    # -- Query methods --

    def get_assessment(self, assessment_id: str) -> Optional[L4Assessment]:
        return self._assessments.get(assessment_id)

    def get_feedbacks(self, assessment_id: str) -> list[ExpertFeedback]:
        return [f for f in self._feedbacks.values() if f.assessment_id == assessment_id]
