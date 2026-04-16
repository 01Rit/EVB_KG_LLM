from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from src.api.schemas import PlanRequest, PlanResponse, HealthResponse
from src.kg.client import Neo4jClient, MilvusClient
from src.graphrag.planner import Planner
from src.graphrag.retriever import MultiPathRetriever
from src.utils.llm_client import LLMClient
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

retriever = MultiPathRetriever(neo4j_client, milvus_client)
planner = Planner(llm_client, retriever)


@router.post('/api/v1/disassembly/plan', response_model=PlanResponse)
async def create_plan(request: PlanRequest):
    try:
        result = await planner.plan(
            query=f'拆卸{request.battery_model}型号电池',
            battery_model=request.battery_model,
            context=request.context,
            debug=request.debug
        )
        return result
    except Exception as e:
        logger.error(f'Plan creation failed: {e}')
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/api/v1/health', response_model=HealthResponse)
async def health_check():
    neo4j_status = 'connected' if neo4j_client.verify_connectivity() else 'disconnected'
    milvus_status = 'connected' if milvus_client and milvus_client.collection else 'not_configured'
    llm_status = 'available'
    
    return HealthResponse(
        status='healthy' if neo4j_status == 'connected' else 'degraded',
        neo4j=neo4j_status,
        milvus=milvus_status,
        llm=llm_status
    )


class SequenceRequest(BaseModel):
    battery_model: str
    components: List[Dict[str, Any]] = []


class AllocateRequest(BaseModel):
    battery_model: str
    sequence: Dict[str, Any]


class GraphRequest(BaseModel):
    battery_model: str
    sequence: Dict[str, Any]
    allocations: List[Dict[str, Any]] = []


@router.post('/api/v1/disassembly/sequence')
async def create_sequence(request: SequenceRequest):
    from src.sequence.planner import SequencePlanner

    planner = SequencePlanner()
    result = planner.plan(request.battery_model, request.components)

    return {'code': 0, 'data': result.model_dump()}


@router.post('/api/v1/disassembly/allocate')
async def allocate_tasks(request: AllocateRequest):
    from src.sequence.planner import DisassemblySequence
    from src.allocator.allocator import HumanRobotAllocator
    from src.utils.llm_client import LLMClient
    from src.config import settings

    sequence = DisassemblySequence(**request.sequence)
    llm = LLMClient(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.llm_model
    )
    allocator = HumanRobotAllocator(llm)
    result = allocator.allocate(sequence)

    return {'code': 0, 'data': result.model_dump()}


@router.post('/api/v1/disassembly/graph')
async def generate_graph(request: GraphRequest):
    from src.sequence.planner import DisassemblySequence
    from src.graph_output.generator import GraphOutputGenerator

    sequence = DisassemblySequence(**request.sequence)
    gen = GraphOutputGenerator()
    result = gen.generate(sequence, request.allocations)

    return {'code': 0, 'data': result.model_dump()}