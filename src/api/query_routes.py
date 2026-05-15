from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class FeedbackRequest(BaseModel):
    question: str
    use_web_search: bool = False


@router.post('/query/feedback')
async def query_feedback(request: FeedbackRequest):
    """问答反馈接口 - 支持SSE流式返回"""

    from src.graphrag.natural_feedback import NaturalLanguageFeedback
    from src.graphrag.retriever import MultiPathRetriever
    from src.graphrag.ranker import EvidenceRanker
    from src.utils.llm_client import LLMClient
    from src.kg.client import Neo4jClient, MilvusClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    milvus = None
    if settings.milvus_host:
        try:
            milvus = MilvusClient(settings.milvus_host, settings.milvus_port)
        except Exception as e:
            logger.warning(f"Milvus connection failed, continuing without Milvus: {e}")
    llm = LLMClient(api_key=settings.openai_api_key, base_url=settings.openai_base_url, model=settings.llm_model)

    retriever = MultiPathRetriever(neo4j, milvus)
    ranker = EvidenceRanker()
    feedback = NaturalLanguageFeedback(retriever, ranker, llm)

    async def event_generator():
        try:
            async for event in feedback.generate_stream(
                question=request.question,
                use_web_search=request.use_web_search
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'event': 'close'}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"SSE error: {e}")
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            neo4j.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post('/query/feedback/sync')
async def query_feedback_sync(request: FeedbackRequest):
    """同步版本的问答反馈"""

    from src.graphrag.natural_feedback import NaturalLanguageFeedback
    from src.graphrag.retriever import MultiPathRetriever
    from src.graphrag.ranker import EvidenceRanker
    from src.utils.llm_client import LLMClient
    from src.kg.client import Neo4jClient, MilvusClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    milvus = None
    if settings.milvus_host:
        try:
            milvus = MilvusClient(settings.milvus_host, settings.milvus_port)
        except Exception as e:
            logger.warning(f"Milvus connection failed, continuing without Milvus: {e}")
    llm = LLMClient(api_key=settings.openai_api_key, base_url=settings.openai_base_url, model=settings.llm_model)

    retriever = MultiPathRetriever(neo4j, milvus)
    ranker = EvidenceRanker()
    feedback = NaturalLanguageFeedback(retriever, ranker, llm)

    final_result = None
    async for event in feedback.generate_stream(
        question=request.question,
        use_web_search=request.use_web_search
    ):
        if event.get('stage') == 'done':
            final_result = event

    neo4j.close()

    if final_result:
        sources = []
        answer = final_result.get('answer', '')
        import re
        source_pattern = r'【来源：([^】]+)】'
        matches = re.findall(source_pattern, answer)
        for m in matches:
            parts = m.split(':')
            if len(parts) >= 2:
                sources.append({'type': parts[0], 'name': parts[1]})

        return {
            'code': 0,
            'message': 'success',
            'data': {
                'answer': answer,
                'sources': sources
            }
        }

    return {'code': 1, 'message': 'Generation failed', 'data': None}


class QueryHistoryItem(BaseModel):
    id: str
    battery_model: str
    result_summary: str
    created_at: str


class DisassemblyPlanRequest(BaseModel):
    battery_model: str
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
