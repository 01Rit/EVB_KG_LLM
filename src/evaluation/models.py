"""L4 Evaluation Layer Pydantic Models."""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class RuleStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    ACTIVE = "active"
    DISABLED = "disabled"


class VersionStatus(str, Enum):
    DRAFT = "draft"
    EVALUATED = "evaluated"
    OPTIMIZED = "optimized"
    ARCHIVED = "archived"


class AssessmentStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    CONFIRMED = "confirmed"
    REVISED = "revised"


class ActionOperation(str, Enum):
    ADD_NODE = "ADD_NODE"
    REMOVE_NODE = "REMOVE_NODE"
    MODIFY_PROPERTY = "MODIFY_PROPERTY"
    ADD_REL = "ADD_REL"
    REMOVE_REL = "REMOVE_REL"
    SWAP_CONNECTION = "SWAP_CONNECTION"


class ActionStatus(str, Enum):
    PROPOSED = "proposed"
    APPLIED = "applied"
    REJECTED = "rejected"


class FeedbackType(str, Enum):
    CONFIRM = "confirm"
    REVISE = "revise"
    REJECT = "reject"
    ADD_KNOWLEDGE = "add_knowledge"


class SuggestionType(str, Enum):
    IMPROVEMENT = "improvement"
    WARNING = "warning"
    INFO = "info"


class Dimension(str, Enum):
    TECHNICAL = "technical"
    ECONOMIC = "economic"
    ENVIRONMENTAL = "environmental"


class Grade(str, Enum):
    EXCELLENT = "优秀"
    GOOD = "良好"
    QUALIFIED = "合格"
    UNQUALIFIED = "不可再制造"


# ── L4 Rule ──

class L4RuleCondition(BaseModel):
    """Single graph-pattern condition for a rule."""
    condition_type: str  # "REQUIRES_CONNECTION", "REQUIRES_TOOL", "REQUIRES_STRUCTURE", "CONSTRAINED_BY"
    target_label: str    # e.g. "螺栓连接", "标准扳手", "可直达"
    target_id: Optional[str] = None
    effect: Optional[float] = None
    fuzzy_threshold: float = 0.6


class L4RuleCreate(BaseModel):
    name: str
    description: str = ""
    conclusion_score: float = Field(ge=0.0, le=1.0)
    conclusion_grade: Grade
    weight: float = 1.0
    conditions: list[L4RuleCondition] = []
    source_doc_id: Optional[str] = None
    dimension: Dimension = Dimension.TECHNICAL


class L4Rule(BaseModel):
    rule_id: str
    name: str
    description: str = ""
    conclusion_score: float
    conclusion_grade: Grade
    weight: float = 1.0
    status: RuleStatus = RuleStatus.PENDING_REVIEW
    conditions: list[L4RuleCondition] = []
    source_doc_id: Optional[str] = None
    hit_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    dimension: Dimension = Dimension.TECHNICAL
    fuzzy_threshold: float = 0.6


# ── Grade Standard ──

class GradeStandard(BaseModel):
    grade_id: str
    name: str
    min_score: float
    max_score: float
    description: str = ""
    recommendation: str = ""


# ── Comparison Reference ──

class ComparisonRef(BaseModel):
    ref_id: str
    name: str
    option_a: str
    option_b: str
    advantage: str
    reason: str = ""
    score_diff: float = 0.0


# ── Feedback Template ──

class FeedbackTemplate(BaseModel):
    template_id: str
    name: str
    condition_pattern: str
    feedback_text: str
    suggestion_type: SuggestionType = SuggestionType.INFO


# ── DesignVersion ──

class DesignVersionCreate(BaseModel):
    design_name: str
    component_ids: list[str] = []
    connection_ids: list[str] = []


class DesignVersion(BaseModel):
    version_id: str
    design_name: str
    version_number: int
    created_by: str = "user"
    status: VersionStatus = VersionStatus.DRAFT
    component_count: int = 0
    created_at: Optional[str] = None


class DesignVersionDetail(DesignVersion):
    components: list[dict] = []
    connections: list[dict] = []
    relationships: list[dict] = []


# ── L4 Assessment ──

class DimensionScore(BaseModel):
    dimension: Dimension
    score: Optional[float] = None
    rsr_value: Optional[float] = None
    rank: Optional[int] = None
    grade: Grade
    matched_rules: int
    total_rules: int


class GradeThreshold(BaseModel):
    excellent: float
    good: float
    qualified: float
    regression: dict


class RuleMatchDetail(BaseModel):
    rule_id: str
    rule_name: str
    matched: bool
    score_contribution: float
    matched_pattern: str = ""
    reason: str = ""


class L4AssessmentCreate(BaseModel):
    version_id: str


class L4Assessment(BaseModel):
    assessment_id: str
    version_id: str
    overall_score: float
    overall_grade: Grade
    rule_matches: list[RuleMatchDetail] = []
    feedback_text: str = ""
    status: AssessmentStatus = AssessmentStatus.PENDING_REVIEW
    created_at: Optional[str] = None
    dimension_scores: list[DimensionScore] = []
    evaluation_mode: str = "single"
    dimension_weights: dict = {}
    grade_thresholds: Optional[GradeThreshold] = None
    rank_matrix: Optional[list[dict]] = None
    per_version: Optional[list[dict]] = None


# ── ReasoningPath ──

class ReasoningPath(BaseModel):
    path_id: str
    assessment_id: str
    matched_rule_ids: list[str] = []
    evaluation_chain: list[RuleMatchDetail] = []
    aggregate_score: float = 0.0
    unmatched_rules: list[dict] = []
    confidence_factors: dict = {}
    created_at: Optional[str] = None


# ── ExpertFeedback ──

class ExpertFeedbackCreate(BaseModel):
    feedback_type: FeedbackType
    original_score: float
    revised_score: Optional[float] = None
    comment: str = ""
    expert_name: str = "anonymous"


class ExpertFeedback(BaseModel):
    feedback_id: str
    assessment_id: str
    feedback_type: FeedbackType
    original_score: float
    revised_score: Optional[float] = None
    comment: str = ""
    expert_name: str = "anonymous"
    created_at: Optional[str] = None


# ── OptimizationAction ──

class OptimizationActionCreate(BaseModel):
    operation: ActionOperation
    target_label: str = ""
    target_id: Optional[str] = None
    payload: dict = {}
    reason: str = ""


class OptimizationAction(BaseModel):
    action_id: str
    assessment_id: str
    operation: ActionOperation
    target_label: str = ""
    target_id: Optional[str] = None
    payload: dict = {}
    reason: str = ""
    status: ActionStatus = ActionStatus.PROPOSED
    created_at: Optional[str] = None


# ── Design Prediction ──

class DesignPredictionRequest(BaseModel):
    """Parameterized input for disassemblability prediction."""
    connection_types: list[str] = []
    tool_requirements: list[str] = []
    structure_features: list[str] = []
    component_count: int = 0
    assembly_mode: str = ""


class DesignPredictionResponse(BaseModel):
    predicted_score: float
    predicted_grade: Grade
    matched_rules: list[RuleMatchDetail] = []
    risk_factors: list[str] = []
    suggestions: list[str] = []


# ── Import ──

class RuleExtractRequest(BaseModel):
    doc_ids: list[str] = []


class CandidateRule(BaseModel):
    """Extracted rule pending review."""
    rule_id: str
    name: str
    description: str = ""
    conclusion_score: float = 0.5
    conclusion_grade: Grade = Grade.QUALIFIED
    weight: float = 1.0
    conditions: list[L4RuleCondition] = []
    source_doc_id: Optional[str] = None
    consistency_valid: bool = False
    consistency_errors: list[str] = []
    dimension: Dimension = Dimension.TECHNICAL
    fuzzy_threshold: float = 0.6
    duplicate_status: Optional[str] = None
    duplicate_of: Optional[str] = None


class ComponentEvalAttributes(BaseModel):
    """15 re-manufacturing attributes extracted from design documents."""
    modularity: str = ""
    connection_type: str = ""
    connection_reversibility: str = ""
    tool_requirements: str = ""
    accessibility: str = ""
    safety_risks: str = ""
    material_type: str = ""
    estimated_time: str = ""
    reusability: str = ""
    inspection_method: str = ""
    seal_type: str = ""
    disassembly_order: str = ""
    reattachment_torque: str = ""
    fault_clearing: str = ""
    hazardous_material: str = ""


class GradeConfig(BaseModel):
    excellent_threshold: float = 0.75
    good_threshold: float = 0.55
    qualified_threshold: float = 0.35
    source: str = "default"
