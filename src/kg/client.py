from neo4j import GraphDatabase
from contextlib import contextmanager
from typing import Generator
import traceback
from pymilvus import connections, Collection
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)


class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.user = user
        self.password = password
        self._driver = None

    @property
    def driver(self):
        if self._driver is None:
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        return self._driver

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None

    @contextmanager
    def session(self) -> Generator:
        driver = self.driver
        session = driver.session()
        try:
            yield session
        finally:
            session.close()
    
    def verify_connectivity(self) -> bool:
        try:
            self.driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error(f'Neo4j connectivity check failed: {e}')
            return False
    
    def execute_query(self, query: str, parameters: Optional[dict] = None):
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    
    def search_components(self, query: str, top_k: int = 30) -> list[dict]:
        cypher = '''
        MATCH (c:Component)
        WHERE c.name CONTAINS $query OR c.battery_model CONTAINS $query
        RETURN COALESCE(c.id, c.name) as id, c.name as name, c.battery_model as battery_model,
               c.tool_required as tool_required, c.safety_level as safety_level
        LIMIT $top_k
        '''
        return self.execute_query(cypher, {'query': query, 'top_k': top_k})

    def get_all_components(self, battery_model: str = None, top_k: int = 100) -> list[dict]:
        if battery_model:
            cypher = '''
            MATCH (c:Component {battery_model: $battery_model})
            RETURN COALESCE(c.id, c.name) as id, c.name as name, c.battery_model as battery_model,
                   c.tool_required as tool_required, c.safety_level as safety_level,
                   c.source_type as source_type,
                   c.as_score as as_score, c.h_weighted_score as h_score,
                   c.s_weighted_score as s_score, c.human_loss as human_loss,
                   c.robot_loss as robot_loss, c.loss_diff as loss_diff,
                   c.assignee as assignee
            LIMIT $top_k
            '''
            return self.execute_query(cypher, {'battery_model': battery_model, 'top_k': top_k})
        else:
            cypher = '''
            MATCH (c:Component)
            RETURN COALESCE(c.id, c.name) as id, c.name as name, c.battery_model as battery_model,
                   c.tool_required as tool_required, c.safety_level as safety_level,
                   c.source_type as source_type,
                   c.as_score as as_score, c.h_weighted_score as h_score,
                   c.s_weighted_score as s_score, c.human_loss as human_loss,
                   c.robot_loss as robot_loss, c.loss_diff as loss_diff,
                   c.assignee as assignee
            LIMIT $top_k
            '''
            return self.execute_query(cypher, {'top_k': top_k})

    def search_l2_entities(self, query: str, top_k: int = 30) -> list[dict]:
        cypher = '''
        MATCH (e:L2_Entity)
        WHERE e.name CONTAINS $query OR e.battery_model CONTAINS $query OR e.entity_type CONTAINS $query
        RETURN e.id as id, e.name as name, e.entity_type as entity_type,
               e.battery_model as battery_model, e.source_evidence as source_evidence,
               e.doc_id as doc_id
        LIMIT $top_k
        '''
        return self.execute_query(cypher, {'query': query, 'top_k': top_k})

    def get_all_l2_entities(self, battery_model: str = None, top_k: int = 100) -> list[dict]:
        if battery_model:
            cypher = '''
            MATCH (e:L2_Entity {battery_model: $battery_model})
            RETURN e.id as id, e.name as name, e.entity_type as entity_type,
                   e.battery_model as battery_model, e.source_evidence as source_evidence,
                   e.doc_id as doc_id
            LIMIT $top_k
            '''
            return self.execute_query(cypher, {'battery_model': battery_model, 'top_k': top_k})
        else:
            cypher = '''
            MATCH (e:L2_Entity)
            RETURN e.id as id, e.name as name, e.entity_type as entity_type,
                   e.battery_model as battery_model, e.source_evidence as source_evidence,
                   e.doc_id as doc_id
            LIMIT $top_k
            '''
            return self.execute_query(cypher, {'top_k': top_k})

    def get_all_relations(self, battery_model: str = None) -> list[dict]:
        if battery_model:
            cypher = '''
            MATCH (c1:Component)-[r]->(c2:Component)
            WHERE c1.battery_model = $battery_model OR c2.battery_model = $battery_model
            RETURN c1.name as head, type(r) as relation, c2.name as tail,
                   r.head_tool as head_tool, r.head_safety as head_safety,
                   r.tail_tool as tail_tool, r.tail_safety as tail_safety
            '''
            return self.execute_query(cypher, {'battery_model': battery_model})
        else:
            cypher = '''
            MATCH (c1:Component)-[r]->(c2:Component)
            RETURN c1.name as head, type(r) as relation, c2.name as tail,
                   r.head_tool as head_tool, r.head_safety as head_safety,
                   r.tail_tool as tail_tool, r.tail_safety as tail_safety
            '''
            return self.execute_query(cypher, {})
    
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
        MATCH path = (c:Component|L2_Entity)-[r*1..{depth}]-(related)
        WHERE COALESCE(c.id, c.name) IN $node_ids
        RETURN nodes(path) as nodes, relationships(path) as rels
        '''

        results = self.execute_query(cypher, {'node_ids': node_ids})

        nodes = []
        edges = []
        seen_nodes = set()
        seen_rels = set()

        for record in results:
            for node in record.get('nodes', []):
                node_id = node.get('id') or node.get('name')
                if node_id and node_id not in seen_nodes:
                    seen_nodes.add(node_id)
                    nodes.append({
                        'id': node_id,
                        'labels': list(node.labels) if hasattr(node, 'labels') else ['Unknown'],
                        'properties': dict(node) if hasattr(node, 'properties') else dict(node)
                    })

            for rel in record.get('rels', []):
                if isinstance(rel, tuple) and len(rel) >= 2:
                    start_node, relationship, end_node = rel[0], rel[1], rel[2]
                    start_id = start_node.get('id') or start_node.get('name') if hasattr(start_node, 'get') else None
                    rel_id = f"{start_id}-{relationship}"
                    if rel_id not in seen_rels:
                        seen_rels.add(rel_id)
                        edges.append({
                            'start': start_id,
                            'end': end_node.get('id') or end_node.get('name') if hasattr(end_node, 'get') else None,
                            'type': relationship if isinstance(relationship, str) else relationship.type,
                            'properties': dict(relationship) if hasattr(relationship, 'properties') else {}
                        })

        return {'nodes': nodes, 'edges': edges}
    
    def get_battery_model_components(self, battery_model: str) -> list[dict]:
        cypher = '''
        MATCH (c:Component {battery_model: $model})
        RETURN COALESCE(c.id, c.name) as id, c.name as name, c.tool_required as tool_required,
               c.safety_level as safety_level
        ORDER BY c.name
        '''
        return self.execute_query(cypher, {'model': battery_model})

    def detect_communities(self, level: int = 2) -> list[dict]:
        """Detect communities using Louvain algorithm."""
        try:
            import networkx as nx
            from community import community_louvain
        except ImportError:
            logger.warning("networkx or python-louvain not installed, returning empty")
            return []

        with self.driver.session() as session:
            result = session.run("""
                MATCH (n)-[r]->(m)
                RETURN n.id AS source, m.id AS target
            """)
            edges = [(record['source'], record['target']) for record in result]

        if not edges:
            return []

        G = nx.Graph()
        G.add_edges_from(edges)

        partition = community_louvain.best_partition(G)

        communities = {}
        for node, comm_id in partition.items():
            if comm_id not in communities:
                communities[comm_id] = []
            communities[comm_id].append(node)

        return [{'id': cid, 'nodes': nodes, 'level': level} for cid, nodes in communities.items()]

    def update_component_properties(self, component_name: str, properties: dict) -> bool:
        """Update component node properties in Neo4j."""
        cypher = '''
        MATCH (c:Component {name: $name})
        SET c += $props
        RETURN c
        '''
        try:
            result = self.execute_query(cypher, {'name': component_name, 'props': properties})
            return len(result) > 0
        except Exception as e:
            logger.error(f"Failed to update component {component_name}: {e}")
            return False

    def get_component_by_name(self, component_name: str, battery_model: str = None) -> Optional[dict]:
        """Get a single component by name."""
        if battery_model:
            cypher = '''
            MATCH (c:Component {name: $name, battery_model: $battery_model})
            RETURN COALESCE(c.id, c.name) as id, c.name as name, c.battery_model as battery_model,
                   c.tool_required as tool_required, c.safety_level as safety_level,
                   c.source_type as source_type
            '''
            results = self.execute_query(cypher, {'name': component_name, 'battery_model': battery_model})
        else:
            cypher = '''
            MATCH (c:Component {name: $name})
            RETURN COALESCE(c.id, c.name) as id, c.name as name, c.battery_model as battery_model,
                   c.tool_required as tool_required, c.safety_level as safety_level,
                   c.source_type as source_type
            '''
            results = self.execute_query(cypher, {'name': component_name})
        return results[0] if results else None

    def get_component_relationships(self, component_name: str, battery_model: str = None) -> dict:
        """Get neighboring components and relationship types for a given component."""
        if battery_model:
            cypher = '''
            MATCH (c:Component {name: $name, battery_model: $battery_model})-[r]-(neighbor)
            RETURN COALESCE(neighbor.name, neighbor.id) as neighbor_name,
                   type(r) as relation_type,
                   r.head_tool as head_tool, r.tail_tool as tail_tool,
                   r.head_safety as head_safety, r.tail_safety as tail_safety
            '''
            results = self.execute_query(cypher, {'name': component_name, 'battery_model': battery_model})
        else:
            cypher = '''
            MATCH (c:Component {name: $name})-[r]-(neighbor)
            RETURN COALESCE(neighbor.name, neighbor.id) as neighbor_name,
                   type(r) as relation_type,
                   r.head_tool as head_tool, r.tail_tool as tail_tool,
                   r.head_safety as head_safety, r.tail_safety as tail_safety
            '''
            results = self.execute_query(cypher, {'name': component_name})
        return {'neighbors': results} if results else {'neighbors': []}

    def get_subgraph_nodes(self, node_ids: list[str]) -> list[dict]:
        """Get node details for a list of node IDs."""
        if not node_ids:
            return []
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n) WHERE n.id IN $ids
                RETURN n.id AS id, labels(n) AS labels, properties(n) AS props
            """, ids=node_ids)
            return [dict(record) for record in result]


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
        
        if not results or not results[0]:
            return []
        return [
            {'id': hit.entity.get('id'), 'text': hit.entity.get('text'), 
             'type': hit.entity.get('type'), 'distance': hit.distance}
            for hit in results[0]
        ]