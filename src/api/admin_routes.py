from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class PromoteRequest(BaseModel):
    doc_id: str
    name: str
    battery_model: str
    tool_required: List[str] = []
    safety_level: int = 1
    precedence: List[str] = []


class DocumentResponse(BaseModel):
    doc_id: str
    title: str
    source: str
    component_count: int


class ComponentResponse(BaseModel):
    id: str
    name: str
    battery_model: str


@router.get('/api/v1/admin/documents')
async def list_documents():
    from src.kg.client import Neo4jClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    cypher = '''
    MATCH (d:Document)
    OPTIONAL MATCH (d)-[:CONTAINS]->(c:Component)
    RETURN d.doc_id as doc_id, d.title as title, d.source as source,
           count(c) as component_count
    ORDER BY d.title
    '''
    try:
        results = neo4j.execute_query(cypher)

        return [DocumentResponse(
            doc_id=r['doc_id'],
            title=r['title'],
            source=r['source'],
            component_count=r['component_count']
        ) for r in results]
    finally:
        neo4j.close()


@router.post('/api/v1/admin/components/promote')
async def promote_document(request: PromoteRequest):
    from src.kg.client import Neo4jClient
    from src.utils.llm_client import LLMClient
    from src.config import settings
    from src.importer.importer import DataImporter

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    llm = LLMClient(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.llm_model
    )

    try:
        importer = DataImporter(neo4j, llm)
        component_data = {
            'name': request.name,
            'battery_model': request.battery_model,
            'tool_required': request.tool_required,
            'safety_level': request.safety_level,
            'precedence': request.precedence
        }

        success = importer.promote_to_component(request.doc_id, component_data)

        if not success:
            raise HTTPException(status_code=500, detail='Promotion failed')

        return {'code': 0, 'message': 'Component promoted successfully'}
    finally:
        neo4j.close()


@router.get('/api/v1/admin/components')
async def list_components():
    from src.kg.client import Neo4jClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    cypher = '''
    MATCH (c:Component {source_type: 'manual'})
    RETURN c.id as id, c.name as name, c.battery_model as battery_model
    ORDER BY c.name
    '''
    try:
        results = neo4j.execute_query(cypher)

        return [ComponentResponse(
            id=r['id'],
            name=r['name'],
            battery_model=r['battery_model']
        ) for r in results]
    finally:
        neo4j.close()


class ScoreAllL1Request(BaseModel):
    battery_model: Optional[str] = None


class ScoreResultResponse(BaseModel):
    component: str
    h_score: float
    s_score: float
    as_score: float
    human_loss: float
    robot_loss: float
    assignee: str


@router.post('/api/v1/admin/components/score-all', response_model=List[ScoreResultResponse])
async def score_all_l1_components(request: ScoreAllL1Request = ScoreAllL1Request()):
    from src.kg.client import Neo4jClient
    from src.utils.llm_client import LLMClient
    from src.allocator.batch_scorer import BatchScorer
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    llm = LLMClient(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.llm_model
    )

    try:
        scorer = BatchScorer(llm, neo4j)
        results = scorer.score_all_l1_components(battery_model=request.battery_model or '')

        return [ScoreResultResponse(
            component=r['component'],
            h_score=r['h_score'],
            s_score=r['s_score'],
            as_score=r['as_score'],
            human_loss=r['human_loss'],
            robot_loss=r['robot_loss'],
            assignee=r['assignee']
        ) for r in results]
    finally:
        neo4j.close()