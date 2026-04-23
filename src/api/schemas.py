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


class Step(BaseModel):
    id: int
    component: str
    action: str
    tool: list[str] = []
    evidence: list[str] = []
    evidence_sources: list[EvidenceSource] = []
    confidence: Optional[float] = None
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