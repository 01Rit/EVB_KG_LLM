from pydantic import BaseModel
from typing import Optional


class PlanRequest(BaseModel):
    battery_model: str
    context: list[str] = []
    debug: bool = False


class Step(BaseModel):
    id: int
    component: str
    action: str
    tool: list[str] = []
    evidence: list[str] = []
    confidence: Optional[float] = None
    safety_level: Optional[int] = None


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