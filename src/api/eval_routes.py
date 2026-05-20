"""L4 Evaluation API routes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.evaluation.models import (
    L4Rule, L4RuleCreate, L4Assessment, RuleStatus, Grade,
)
from src.evaluation.rule_engine import RuleEngine
from src.evaluation.evaluator import Evaluator
from src.evaluation.feedback_generator import FeedbackGenerator
from src.kg.client import Neo4jClient
from src.config import settings

import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Shared instances ──
neo4j_client = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
rule_engine = RuleEngine(neo4j_client)
evaluator = Evaluator(rule_engine)
feedback_gen = FeedbackGenerator()


# ── Request/Response schemas ──

class EvaluateRequest(BaseModel):
    version_id: str
    subgraph: dict  # {"nodes": [...], "relationships": [...]}


class RuleUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    conclusion_score: Optional[float] = None
    conclusion_grade: Optional[Grade] = None
    weight: Optional[float] = None
    status: Optional[RuleStatus] = None


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "Success"
    data: Optional[dict] = None


# ── Rule CRUD ──

@router.post("/api/v1/evaluation/rules", response_model=ApiResponse)
async def create_rule(request: L4RuleCreate):
    try:
        rule = rule_engine.create_rule(request)
        return ApiResponse(data=rule.model_dump())
    except Exception as e:
        logger.error(f"Create rule failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/evaluation/rules", response_model=ApiResponse)
async def list_rules(status: Optional[str] = None):
    try:
        filter_status = RuleStatus(status) if status else None
        rules = rule_engine.get_rules(status=filter_status)
        return ApiResponse(data={"rules": [r.model_dump() for r in rules], "total": len(rules)})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    except Exception as e:
        logger.error(f"List rules failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/evaluation/rules/{rule_id}", response_model=ApiResponse)
async def get_rule(rule_id: str):
    rule = rule_engine.get_rule_by_id(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")
    return ApiResponse(data=rule.model_dump())


@router.put("/api/v1/evaluation/rules/{rule_id}", response_model=ApiResponse)
async def update_rule(rule_id: str, request: RuleUpdateRequest):
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    rule = rule_engine.update_rule(rule_id, **updates)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")
    return ApiResponse(data=rule.model_dump())


@router.delete("/api/v1/evaluation/rules/{rule_id}", response_model=ApiResponse)
async def delete_rule(rule_id: str):
    if not rule_engine.delete_rule(rule_id):
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")
    return ApiResponse(data={"deleted": True})


# ── Evaluation ──

@router.post("/api/v1/evaluation/evaluate", response_model=ApiResponse)
async def evaluate_design(request: EvaluateRequest):
    try:
        assessment = evaluator.evaluate(request.version_id, request.subgraph)
        return ApiResponse(data=assessment.model_dump())
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Feedback ──

@router.post("/api/v1/evaluation/feedback", response_model=ApiResponse)
async def generate_feedback(assessment: L4Assessment):
    try:
        active_rules = rule_engine.get_rules(status=RuleStatus.ACTIVE)
        feedback = feedback_gen.generate(assessment, active_rules)
        return ApiResponse(data=feedback)
    except Exception as e:
        logger.error(f"Feedback generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
