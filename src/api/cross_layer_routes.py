from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from src.kg.client import Neo4jClient, MilvusClient
from src.utils.llm_client import LLMClient
from src.graphrag.cross_layer_retriever import CrossLayerRetriever
from src.cross_layer.batch_builder import CrossLayerBatchBuilder
from src.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

neo4j_client = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
try:
    milvus_client = MilvusClient(settings.milvus_host, settings.milvus_port) if settings.milvus_host else None
except Exception:
    milvus_client = None
llm_client = LLMClient(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
    model=settings.llm_model,
    temperature=settings.temperature,
    max_tokens=settings.max_tokens
)
cross_layer_retriever = CrossLayerRetriever(neo4j_client, milvus_client, llm_client)


class CrossLayerTriggerRequest(BaseModel):
    battery_model: Optional[str] = None
    intents: List[str]
    relation_types: List[str] = ["REFERENCE_OF", "DEFINITION_OF"]


class CrossLayerTriggerResponse(BaseModel):
    code: int = 0
    message: str = "Success"
    data: dict = {}


@router.post("/api/v1/cross-layer/trigger", response_model=CrossLayerTriggerResponse)
async def trigger_cross_layer(request: CrossLayerTriggerRequest):
    try:
        graph = cross_layer_retriever.retrieve_cross_layer(
            battery_model=request.battery_model,
            intents=request.intents,
        )
        return CrossLayerTriggerResponse(
            code=0,
            message="Success",
            data={
                "nodes_retrieved": len(graph.nodes),
                "edges_retrieved": len(graph.edges),
            }
        )
    except Exception as e:
        logger.error(f"Cross-layer trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/cross-layer/build-all")
async def build_cross_layer_all():
    """
    Batch build all cross-layer relations (full rebuild).

    Layer 1: REFERENCE_OF (L1→L2) - deterministic, K=5 per node
    Layer 2: DEFINITION_OF (L2→L3) - weak semantic, K=3 + threshold

    Returns integrity check results including orphan detection.
    """
    try:
        builder = CrossLayerBatchBuilder(neo4j_client, milvus_client, llm_client)
        result = builder.build_all()

        return {
            'code': 0,
            'message': 'Cross-layer build completed',
            'data': result,
        }
    except Exception as e:
        logger.error(f"Cross-layer build-all failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))