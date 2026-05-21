"""L4 Evaluation API routes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.evaluation.models import (
    L4Rule, L4RuleCreate, L4Assessment, L4AssessmentCreate,
    DesignVersionCreate, ExpertFeedbackCreate,
    OptimizationActionCreate, DesignPredictionRequest,
    RuleExtractRequest, RuleStatus, Grade, GradeConfig,
)
from src.evaluation.rule_engine import RuleEngine
from src.evaluation.evaluator import Evaluator
from src.evaluation.feedback_generator import FeedbackGenerator
from src.evaluation.version_manager import VersionManager
from src.evaluation.action_executor import ActionExecutor
from src.evaluation.closed_loop import ClosedLoop
from src.evaluation.import_handler import ImportHandler
from src.kg.client import Neo4jClient
from src.utils.llm_client import LLMClient
from src.config import settings

import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Shared instances ──
neo4j_client = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
llm_client = LLMClient(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
    model=settings.llm_model,
)
closed_loop = ClosedLoop(neo4j_client, llm_client)
import_handler = ImportHandler(neo4j_client, llm_client)


# ── Request/Response schemas ──

class RuleUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    conclusion_score: Optional[float] = None
    conclusion_grade: Optional[Grade] = None
    weight: Optional[float] = None
    status: Optional[RuleStatus] = None
    dimension: Optional[str] = None
    fuzzy_threshold: Optional[float] = None


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "Success"
    data: Optional[dict] = None


# ── Rule CRUD ──

@router.post("/api/v1/evaluation/rules", response_model=ApiResponse)
async def create_rule(request: L4RuleCreate):
    try:
        rule = closed_loop.rule_engine.create_rule(request)
        return ApiResponse(data=rule.model_dump())
    except Exception as e:
        logger.error(f"Create rule failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/evaluation/rules", response_model=ApiResponse)
async def list_rules(status: Optional[str] = None):
    try:
        filter_status = RuleStatus(status) if status else None
        rules = closed_loop.rule_engine.get_rules(status=filter_status)
        return ApiResponse(data={"rules": [r.model_dump() for r in rules], "total": len(rules)})
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    except Exception as e:
        logger.error(f"List rules failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/evaluation/rules/{rule_id}", response_model=ApiResponse)
async def get_rule(rule_id: str):
    rule = closed_loop.rule_engine.get_rule_by_id(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")
    return ApiResponse(data=rule.model_dump())


@router.put("/api/v1/evaluation/rules/{rule_id}", response_model=ApiResponse)
async def update_rule(rule_id: str, request: RuleUpdateRequest):
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    rule = closed_loop.rule_engine.update_rule(rule_id, **updates)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")
    return ApiResponse(data=rule.model_dump())


@router.delete("/api/v1/evaluation/rules/{rule_id}", response_model=ApiResponse)
async def delete_rule(rule_id: str):
    if not closed_loop.rule_engine.delete_rule(rule_id):
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")
    return ApiResponse(data={"deleted": True})


# ── Design Version Management ──

@router.post("/api/v1/evaluation/versions", response_model=ApiResponse)
async def create_version(data: DesignVersionCreate):
    try:
        version = closed_loop.version_manager.create_version(data)
        return ApiResponse(data=version.model_dump())
    except Exception as e:
        logger.error(f"Create version failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/evaluation/versions", response_model=ApiResponse)
async def list_versions(design_name: Optional[str] = None):
    try:
        versions = closed_loop.version_manager.list_versions(design_name=design_name)
        return ApiResponse(data={"versions": [v.model_dump() for v in versions], "total": len(versions)})
    except Exception as e:
        logger.error(f"List versions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/evaluation/versions/{version_id}", response_model=ApiResponse)
async def get_version(version_id: str):
    detail = closed_loop.version_manager.get_version_detail(version_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Version not found")
    return ApiResponse(data=detail.model_dump())


@router.get("/api/v1/evaluation/versions/{v1_id}/diff/{v2_id}", response_model=ApiResponse)
async def diff_versions(v1_id: str, v2_id: str):
    diff = closed_loop.version_manager.diff_versions(v1_id, v2_id)
    return ApiResponse(data=diff)


# ── Assessment (Core Closed Loop) ──

@router.post("/api/v1/evaluation/assess", response_model=ApiResponse)
async def assess_version(data: L4AssessmentCreate):
    try:
        assessment = closed_loop.reason(data.version_id)
        return ApiResponse(data=assessment.model_dump())
    except Exception as e:
        logger.error(f"Assessment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/evaluation/assessments/{assessment_id}", response_model=ApiResponse)
async def get_assessment(assessment_id: str):
    assessment = closed_loop.get_assessment(assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return ApiResponse(data=assessment.model_dump())


@router.post("/api/v1/evaluation/assessments/{assessment_id}/feedback", response_model=ApiResponse)
async def expert_feedback(assessment_id: str, data: ExpertFeedbackCreate):
    fb = closed_loop.correct(assessment_id, data)
    if not fb:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return ApiResponse(data=fb.model_dump())


@router.post("/api/v1/evaluation/assessments/{assessment_id}/feedback-text", response_model=ApiResponse)
async def get_feedback_text(assessment_id: str):
    result = closed_loop.generate_feedback(assessment_id)
    return ApiResponse(data=result)


@router.post("/api/v1/evaluation/assessments/{assessment_id}/optimize", response_model=ApiResponse)
async def generate_actions(assessment_id: str):
    actions = closed_loop.generate_actions(assessment_id)
    return ApiResponse(data={"actions": [a.model_dump() for a in actions]})


@router.post("/api/v1/evaluation/actions/apply", response_model=ApiResponse)
async def apply_actions(data: dict):
    version_id = data.get("version_id")
    action_ids = data.get("action_ids", [])
    if not version_id:
        raise HTTPException(status_code=400, detail="version_id required")
    try:
        new_version = closed_loop.apply_and_new_version(version_id, action_ids)
        return ApiResponse(data=new_version.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Design Prediction ──

@router.post("/api/v1/evaluation/predict", response_model=ApiResponse)
async def predict_design(data: DesignPredictionRequest):
    """Predict disassemblability from parameterized design input."""
    try:
        subgraph = {"nodes": [{"id": "pred_comp", "labels": ["L1_Component"], "name": "Prediction Target"}], "relationships": []}
        for ct in data.connection_types:
            nid = f"pred_conn_{ct}"
            subgraph["nodes"].append({"id": nid, "labels": ["ConnectionType"], "name": ct})
            subgraph["relationships"].append({"start": "pred_comp", "end": nid, "type": "USES_CONNECTION"})
        for tf in data.tool_requirements:
            nid = f"pred_tool_{tf}"
            subgraph["nodes"].append({"id": nid, "labels": ["ToolType"], "name": tf})
            subgraph["relationships"].append({"start": "pred_comp", "end": nid, "type": "REQUIRES_TOOL"})
        for sf in data.structure_features:
            nid = f"pred_feat_{sf}"
            subgraph["nodes"].append({"id": nid, "labels": ["StructureFeature"], "name": sf})
            subgraph["relationships"].append({"start": "pred_comp", "end": nid, "type": "HAS_FEATURE"})

        assessment = closed_loop.evaluator.evaluate("predict_preview", subgraph)

        score = assessment.overall_score
        grade = assessment.overall_grade
        matches = assessment.rule_matches
        risk_factors = [m.rule_name for m in matches if not m.matched]
        suggestions = []
        if score < 0.4:
            suggestions.append("建议重新评估连接方式，优先采用螺栓或卡扣连接")
        if data.tool_requirements and any("special" in t.lower() or "专用" in t for t in data.tool_requirements):
            suggestions.append("Specialized tools increase disassembly cost, consider standard tools")

        from src.evaluation.models import DesignPredictionResponse
        return ApiResponse(data=DesignPredictionResponse(
            predicted_score=score, predicted_grade=grade,
            matched_rules=matches, risk_factors=risk_factors, suggestions=suggestions,
        ).model_dump())
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Batch Assessment ──

@router.post("/api/v1/evaluation/batch-assess", response_model=ApiResponse)
async def batch_assess(data: dict):
    version_ids = data.get("version_ids", [])
    if not version_ids:
        raise HTTPException(status_code=400, detail="至少选择一个设计版本")
    try:
        assessments = closed_loop.batch_assess(version_ids)
        return ApiResponse(data={
            "assessments": [a.model_dump() for a in assessments],
            "grade_thresholds": assessments[0].grade_thresholds.model_dump() if assessments and assessments[0].grade_thresholds else None,
        })
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Batch assessment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Grade Config ──

@router.get("/api/v1/evaluation/grade-config", response_model=ApiResponse)
async def get_grade_config():
    return ApiResponse(data=closed_loop.get_grade_config().model_dump())


@router.put("/api/v1/evaluation/grade-config", response_model=ApiResponse)
async def update_grade_config(data: dict):
    config = GradeConfig(**data)
    return ApiResponse(data=closed_loop.update_grade_config(config).model_dump())


@router.post("/api/v1/evaluation/grade-config/calibrate", response_model=ApiResponse)
async def calibrate_thresholds():
    try:
        return ApiResponse(data=closed_loop.calibrate_thresholds().model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Import (Rule Extraction) ──

@router.post("/api/v1/evaluation/import/extract", response_model=ApiResponse)
async def extract_rules(data: RuleExtractRequest):
    try:
        logger.info(f"Extracting rules from docs: {data.doc_ids}")
        logger.info(f"import_handler id: {id(import_handler)}")
        logger.info(f"LLM max_tokens: {import_handler.llm.max_tokens}")
        candidates = import_handler.extract_from_docs(data.doc_ids)
        logger.info(f"Extracted {len(candidates)} candidates")
        validated = import_handler.check_consistency(candidates)
        logger.info(f"Validated {len(validated)} candidates")
        return ApiResponse(data={"candidates": [c.model_dump() for c in validated]})
    except Exception as e:
        logger.error(f"Rule extraction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/evaluation/import/candidates", response_model=ApiResponse)
async def list_candidates():
    candidates = import_handler.get_candidates()
    return ApiResponse(data={"candidates": [c.model_dump() for c in candidates]})


@router.post("/api/v1/evaluation/import/approve/{candidate_id}", response_model=ApiResponse)
async def approve_candidate(candidate_id: str):
    from src.evaluation.models import L4RuleCreate
    cand = import_handler.get_candidates()
    cand_map = {c.rule_id: c for c in cand}
    if candidate_id not in cand_map:
        raise HTTPException(status_code=404, detail="Candidate not found")
    c = cand_map[candidate_id]
    rule = closed_loop.rule_engine.create_rule(L4RuleCreate(
        name=c.name,
        description=c.description,
        conclusion_score=c.conclusion_score,
        conclusion_grade=c.conclusion_grade,
        weight=c.weight,
        conditions=c.conditions,
        source_doc_id=c.source_doc_id,
        dimension=c.dimension,
    ))
    import_handler.reject_candidate(candidate_id)
    return ApiResponse(data=rule.model_dump())


@router.post("/api/v1/evaluation/import/reject/{candidate_id}", response_model=ApiResponse)
async def reject_candidate(candidate_id: str):
    ok = import_handler.reject_candidate(candidate_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return ApiResponse(data={"rejected": True})


# ── Component Eval Attributes ──

@router.get("/api/v1/evaluation/components/{component_id}/eval-attributes", response_model=ApiResponse)
async def get_component_eval_attributes(component_id: str):
    try:
        rows = closed_loop.rule_engine.neo4j.execute_query(
            "MATCH (c:Component {id: $id}) RETURN c.eval_attributes AS attrs, c.name AS name",
            {"id": component_id},
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Component not found")
        attrs = {}
        raw = rows[0].get("attrs")
        if raw:
            import json
            try:
                attrs = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                pass
        return ApiResponse(data={"component_id": component_id, "name": rows[0].get("name", ""), "eval_attributes": attrs})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/v1/evaluation/components/{component_id}/eval-attributes", response_model=ApiResponse)
async def update_component_eval_attributes(component_id: str, data: dict):
    try:
        import json
        rows = closed_loop.rule_engine.neo4j.execute_query(
            "MATCH (c:Component {id: $id}) RETURN c.name AS name",
            {"id": component_id},
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Component not found")
        closed_loop.rule_engine.neo4j.execute_query(
            "MATCH (c:Component {id: $id}) SET c.eval_attributes = $attrs",
            {"id": component_id, "attrs": json.dumps(data, ensure_ascii=False)},
        )
        return ApiResponse(data={"component_id": component_id, "eval_attributes": data})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
