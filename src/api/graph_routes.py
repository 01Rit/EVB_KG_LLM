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


def _map_display_type(labels: list[str]) -> str:
    """Map Neo4j label(s) to display type (L1/L2/L3)."""
    for label in labels:
        if label == 'Component':
            return 'L1'
        if label in ('L2_Document', 'L2_Entity'):
            return 'L2'
        if label == 'L3_Term':
            return 'L3'
    # fallback: check prefix
    if any(l.startswith('L2') for l in labels):
        return 'L2'
    if any(l.startswith('L3') for l in labels):
        return 'L3'
    return labels[0] if labels else 'Unknown'


@router.get('/graph/nodes', response_model=List[GraphNodeResponse])
async def get_nodes():
    from src.kg.client import Neo4jClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    cypher = '''
    MATCH (n)
    WHERE n:Component OR n:L2_Document OR n:L2_Entity OR n:L3_Term
          OR n:Document OR n:Term
    RETURN COALESCE(n.id, n.name) as id,
           COALESCE(n.name, n.title, n.term_id) as name,
           labels(n) as node_labels,
           properties(n) as properties
    LIMIT 1000
    '''

    try:
        results = neo4j.execute_query(cypher)

        nodes = []
        for r in results:
            labels = r.get('node_labels', [])
            display_type = _map_display_type(labels)

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
    WHERE (n:Component OR n:L2_Document OR n:L2_Entity OR n:L3_Term OR n:Document OR n:Term)
      AND (n.id = $node_id OR n.name = $node_id)
    RETURN COALESCE(n.id, n.name) as id,
           COALESCE(n.name, n.title, n.term_id) as name,
           labels(n) as node_labels,
           properties(n) as properties
    LIMIT 1
    '''

    try:
        results = neo4j.execute_query(cypher, {'node_id': node_id})

        if not results:
            raise HTTPException(status_code=404, detail='Node not found')

        r = results[0]
        labels = r.get('node_labels', [])
        display_type = _map_display_type(labels)

        return GraphNodeResponse(
            id=r.get('id', ''),
            name=r.get('name', ''),
            type=display_type,
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
    WHERE (a:Component OR a:L2_Document OR a:L2_Entity OR a:L3_Term OR a:Document OR a:Term)
      AND (b:Component OR b:L2_Document OR b:L2_Entity OR b:L3_Term OR b:Document OR b:Term)
    RETURN COALESCE(a.id, a.name) as from_id, COALESCE(b.id, b.name) as to_id, type(r) as type
    LIMIT 2000
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

    # Map display type to Neo4j labels
    type_label_map = {
        'L1': ['Component'],
        'L2': ['L2_Document', 'L2_Entity'],
        'L3': ['L3_Term'],
    }

    if node_type and node_type in type_label_map:
        labels = type_label_map[node_type]
    else:
        labels = ['Component', 'L2_Document', 'L2_Entity', 'L3_Term', 'Document', 'Term']

    label_conditions = ' OR '.join(f'n:{label}' for label in labels)

    cypher = f'''
    MATCH (n)
    WHERE ({label_conditions})
      AND (n.name CONTAINS $q OR COALESCE(n.id, '') CONTAINS $q)
    RETURN COALESCE(n.id, n.name) as id, n.name as name, labels(n) as node_labels, properties(n) as properties
    LIMIT 50
    '''

    try:
        results = neo4j.execute_query(cypher, {'q': q})

        nodes = []
        for r in results:
            labels_list = r.get('node_labels', [])
            display_type = _map_display_type(labels_list)

            nodes.append(GraphNodeResponse(
                id=r.get('id', ''),
                name=r.get('name', ''),
                type=display_type,
                properties=r.get('properties', {})
            ))

        return nodes
    finally:
        neo4j.close()
