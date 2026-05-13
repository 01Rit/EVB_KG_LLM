from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class PlanRequest(BaseModel):
    battery_model: str
    context: list[str] = []
    debug: bool = False


class EvidenceSource(BaseModel):
    node_id: str
    node_type: str
    name: str
    text: Optional[str] = None
    properties: Optional[dict[str, Any]] = None


class ReasoningLink(BaseModel):
    """推理链中的一个论点 — 绑定具体证据"""
    claim: str
    evidence_id: str
    evidence_name: str
    evidence_layer: int  # 1=L1, 2=L2, 3=L3
    evidence_snippet: str
    confidence: float


class StepReasoningChain(BaseModel):
    """一个拆卸步骤的完整推理链"""
    step_id: str
    links: List[ReasoningLink]
    overall_reasoning: str


class ConfidenceInfo(BaseModel):
    """层次化置信度结果"""
    overall: float
    grade: str  # "PASS" | "WARN_CONSISTENCY" | "FAIL_DEPTH" | "FAIL_COVERAGE"
    evidence_coverage: float
    cross_layer_depth_score: float
    consistency: float
    method: str = "hierarchical_gates"


class Step(BaseModel):
    id: int
    component: str
    action: str
    tool: list[str] = []
    evidence: list[str] = []
    evidence_sources: list[EvidenceSource] = []
    confidence: Optional[float] = None
    reasoning_chain: Optional[StepReasoningChain] = None
    confidence_info: Optional[ConfidenceInfo] = None
    safety_level: Optional[int] = None
    h_score: Optional[float] = None
    s_score: Optional[float] = None
    as_score: Optional[float] = None
    human_loss: Optional[float] = None
    robot_loss: Optional[float] = None
    loss_diff: Optional[float] = None
    assignee: Optional[str] = None
    remanufacturing_pathway: Optional[str] = None
    pathway_confidence: Optional[float] = None
    pathway_scores: Optional[dict[str, float]] = None


class FeedbackResponse(BaseModel):
    """FeedbackLoop 返回结果"""
    plan: Dict[str, Any]
    reasoning_traces: List[Dict[str, Any]]  # 每轮迭代的 ReasoningTrace
    total_iterations: int
    final_confidence: float


class PlanResponse(BaseModel):
    code: int = 0
    message: str = 'Success'
    data: Optional[dict] = None


class HealthResponse(BaseModel):
    status: str
    neo4j: str
    milvus: str
    llm: str


class ErrorResponse(BaseModel):
    code: int
    message: str
    detail: Optional[str] = None


class L2EntityData(BaseModel):
    name: str
    entity_type: str
    source_evidence: Optional[str] = None
    properties: Dict[str, Any] = {}


class L2DocumentData(BaseModel):
    title: str
    filename: str
    chapter: Optional[str] = None
    full_text: str
    entities: List[L2EntityData] = []
    terms: List[Dict[str, str]] = []


class L3TermData(BaseModel):
    term_id: str
    name: str
    definition: str
    source_document_id: Optional[str] = None


class L2ImportResponse(BaseModel):
    code: int
    message: str
    doc_id: str
    entities_created: int
    terms_created: int
    relations_created: int
    errors: List[str] = []