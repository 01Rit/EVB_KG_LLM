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


@router.post('/disassembly/plan')
async def create_plan(
    battery_model: str,
    context: List[str] = [],
    debug: bool = False
):
    from src.graphrag.planner import Planner
    from src.kg.client import Neo4jClient
    from src.utils.llm_client import LLMClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    llm = LLMClient(settings.openai_api_key, settings.openai_base_url)

    from src.graphrag.retriever import MultiPathRetriever

    retriever = MultiPathRetriever(neo4j, None)
    planner = Planner(llm, retriever)

    result = await planner.plan(
        query=f"拆卸{battery_model}型号电池",
        battery_model=battery_model,
        context=context,
        debug=debug
    )

    neo4j.close()
    return result


@router.get('/query/history')
async def get_history(limit: int = 10):
    return []


@router.get('/query/history/{limit}')
async def get_history_by_limit(limit: int):
    return []
