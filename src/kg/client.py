from neo4j import GraphDatabase
from pymilvus import connections, Collection
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)


class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def verify_connectivity(self) -> bool:
        try:
            self.driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error(f'Neo4j connectivity check failed: {e}')
            return False
    
    def execute_query(self, query: str, parameters: dict = None):
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    
    def search_components(self, query: str, top_k: int = 30) -> list[dict]:
        cypher = '''
        MATCH (c:Component)
        WHERE c.name CONTAINS $query OR c.battery_model CONTAINS $query
        RETURN c.id as id, c.name as name, c.battery_model as battery_model,
               c.tool_required as tool_required, c.safety_level as safety_level
        LIMIT $top_k
        '''
        return self.execute_query(cypher, {'query': query, 'top_k': top_k})
    
    def search_documents(self, query: str, top_k: int = 30) -> list[dict]:
        cypher = '''
        MATCH (d:Document)
        WHERE d.title CONTAINS $query OR d.content CONTAINS $query
        RETURN d.doc_id as doc_id, d.title as title, d.source as source,
               d.source_type as source_type, d.content as content
        LIMIT $top_k
        '''
        return self.execute_query(cypher, {'query': query, 'top_k': top_k})
    
    def search_terms(self, query: str, top_k: int = 30) -> list[dict]:
        cypher = '''
        MATCH (t:Term)
        WHERE t.term_id CONTAINS $query OR t.definition CONTAINS $query
        RETURN t.term_id as term_id, t.definition as definition, t.units as units
        LIMIT $top_k
        '''
        return self.execute_query(cypher, {'query': query, 'top_k': top_k})
    
    def get_subgraph(self, node_ids: list[str], depth: int = 2) -> dict:
        if not node_ids:
            return {'nodes': [], 'edges': []}
        
        cypher = f'''
        MATCH path = (c:Component)-[r*1..{depth}]-(related)
        WHERE c.id IN $node_ids
        RETURN nodes(path) as nodes, relationships(path) as rels
        '''
        
        results = self.execute_query(cypher, {'node_ids': node_ids})
        
        nodes = []
        edges = []
        seen_nodes = set()
        seen_rels = set()
        
        for record in results:
            for node in record.get('nodes', []):
                if node.element_id not in seen_nodes:
                    seen_nodes.add(node.element_id)
                    nodes.append({
                        'id': node.get('id'),
                        'labels': list(node.labels),
                        'properties': dict(node)
                    })
            
            for rel in record.get('rels', []):
                rel_key = f'{rel.start_node.element_id}-{rel.element_id}'
                if rel_key not in seen_rels:
                    seen_rels.add(rel_key)
                    edges.append({
                        'start': rel.start_node.get('id'),
                        'end': rel.end_node.get('id'),
                        'type': rel.type,
                        'properties': dict(rel)
                    })
        
        return {'nodes': nodes, 'edges': edges}
    
    def get_battery_model_components(self, battery_model: str) -> list[dict]:
        cypher = '''
        MATCH (c:Component {battery_model: $model})
        RETURN c.id as id, c.name as name, c.tool_required as tool_required,
               c.safety_level as safety_level
        ORDER BY c.name
        '''
        return self.execute_query(cypher, {'model': battery_model})


class MilvusClient:
    def __init__(self, host: str, port: int):
        connections.connect(alias='default', host=host, port=port)
        self.collection: Optional[Collection] = None
    
    def close(self):
        connections.disconnect(alias='default')
    
    def set_collection(self, name: str):
        self.collection = Collection(name)
        self.collection.load()
    
    def search(self, query_vector: list[float], top_k: int = 30) -> list[dict]:
        if not self.collection:
            raise RuntimeError('Collection not initialized')
        
        search_params = {'metric_type': 'COSINE', 'params': {}}
        results = self.collection.search(
            data=[query_vector],
            anns_field='embedding',
            param=search_params,
            limit=top_k,
            output_fields=['id', 'text', 'type']
        )
        
        return [
            {'id': hit.entity.get('id'), 'text': hit.entity.get('text'), 
             'type': hit.entity.get('type'), 'distance': hit.distance}
            for hit in results[0]
        ]