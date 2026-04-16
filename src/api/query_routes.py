from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

router = APIRouter()


class QueryHistoryItem(BaseModel):
    id: str
    battery_model: str
    context: List[str]
    result_summary: str
    created_at: str


class DisassemblyPlanRequest(BaseModel):
    battery_model: str
    context: List[str] = []
    debug: bool = False
    mode: str = "local"


@router.post('/disassembly/plan')
async def create_plan(request: DisassemblyPlanRequest):
    from src.graphrag.planner import Planner
    from src.kg.client import Neo4jClient
    from src.utils.llm_client import LLMClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    llm = LLMClient(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.llm_model
    )

    try:
        from src.graphrag.retriever import MultiPathRetriever

        retriever = MultiPathRetriever(neo4j, None)
        planner = Planner(llm, retriever, neo4j)

        result = await planner.plan(
            query=f"拆卸{request.battery_model}型号电池",
            battery_model=request.battery_model,
            context=request.context,
            mode=request.mode,
            debug=request.debug
        )

        return result
    finally:
        neo4j.close()


@router.get('/query/history')
async def get_history(limit: int = 10):
    return []


@router.get('/query/history/{limit}')
async def get_history_by_limit(limit: int):
    return []
