from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

router = APIRouter()


class GraphNodeResponse(BaseModel):
    id: str
    name: str
    type: str
    properties: Dict[str, Any]


class GraphEdgeResponse(BaseModel):
    from_: str
    to: str
    type: str

    class Config:
        populate_by_name = True


@router.get('/graph/nodes', response_model=List[GraphNodeResponse])
async def get_nodes():
    from src.kg.client import Neo4jClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    cypher = '''
    MATCH (n)
    WHERE n:Component OR n:Document OR n:Term
    RETURN COALESCE(n.id, n.name) as id,
           COALESCE(n.name, n.title, n.term_id) as name,
           labels(n)[0] as type,
           properties(n) as properties
    LIMIT 500
    '''

    try:
        results = neo4j.execute_query(cypher)

        nodes = []
        for r in results:
            node_type = r.get('type', 'Unknown')
            if node_type == 'Component':
                display_type = 'L1'
            elif node_type == 'Document':
                display_type = 'L2'
            else:
                display_type = 'L3'

            nodes.append(GraphNodeResponse(
                id=r.get('id', ''),
                name=r.get('name', ''),
                type=display_type,
                properties=r.get('properties', {})
            ))

        return nodes
    finally:
        neo4j.close()


@router.get('/graph/node/{node_id}', response_model=GraphNodeResponse)
async def get_node(node_id: str):
    from src.kg.client import Neo4jClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    cypher = '''
    MATCH (n)
    WHERE n.id = $node_id OR n.name = $node_id
    RETURN COALESCE(n.id, n.name) as id,
           COALESCE(n.name, n.title, n.term_id) as name,
           labels(n)[0] as type,
           properties(n) as properties
    LIMIT 1
    '''

    try:
        results = neo4j.execute_query(cypher, {'node_id': node_id})

        if not results:
            raise HTTPException(status_code=404, detail='Node not found')

        r = results[0]
        node_type = r.get('type', 'Unknown')

        return GraphNodeResponse(
            id=r.get('id', ''),
            name=r.get('name', ''),
            type=node_type,
            properties=r.get('properties', {})
        )
    finally:
        neo4j.close()


@router.get('/graph/relationships', response_model=List[GraphEdgeResponse])
async def get_relationships():
    from src.kg.client import Neo4jClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    cypher = '''
    MATCH (a)-[r]->(b)
    WHERE a:Component OR a:Document OR a:Term
    RETURN COALESCE(a.id, a.name) as from_id, COALESCE(b.id, b.name) as to_id, type(r) as type
    LIMIT 1000
    '''

    try:
        results = neo4j.execute_query(cypher)

        edges = []
        for r in results:
            edges.append(GraphEdgeResponse(
                from_=r.get('from_id', ''),
                to=r.get('to_id', ''),
                type=r.get('type', '')
            ))

        return edges
    finally:
        neo4j.close()


@router.get('/graph/search')
async def search_nodes(q: str, node_type: Optional[str] = None):
    from src.kg.client import Neo4jClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    if node_type:
        label = node_type
    else:
        label = 'Component'

    cypher = f'''
    MATCH (n:{label})
    WHERE n.name CONTAINS $q OR COALESCE(n.id, '') CONTAINS $q
    RETURN COALESCE(n.id, n.name) as id, n.name as name, '{label}' as type, properties(n) as properties
    LIMIT 50
    '''

    try:
        results = neo4j.execute_query(cypher, {'q': q})

        nodes = []
        for r in results:
            nodes.append(GraphNodeResponse(
                id=r.get('id', ''),
                name=r.get('name', ''),
                type=label,
                properties=r.get('properties', {})
            ))

        return nodes
    finally:
        neo4j.close()
