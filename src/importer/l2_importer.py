from src.kg.client import Neo4jClient
from src.importer.entity_extractor import EntityExtractor
from src.utils.llm_client import LLMClient
from typing import Dict, Any, List, Tuple
import uuid
import logging

logger = logging.getLogger(__name__)


class L2Importer:
    def __init__(self, neo4j_client: Neo4jClient, llm_client: LLMClient):
        self.neo4j = neo4j_client
        self.extractor = EntityExtractor(llm_client)

    def import_pdf(self, full_text: str, filename: str) -> Dict[str, Any]:
        extraction = self.extractor.extract_entities_with_types(full_text, filename=filename)
        entities = extraction.get('entities', [])
        terms = extraction.get('terms', [])

        doc_id = str(uuid.uuid4())
        self._create_l2_document(doc_id, filename, full_text)

        entities_created = self._create_l2_entities(doc_id, entities)
        terms_created = self._create_l3_terms(doc_id, terms)
        relations = self._create_cross_layer_relations(doc_id, entities, terms)

        return {
            'doc_id': doc_id,
            'entities_created': entities_created,
            'terms_created': terms_created,
            'relations_created': relations,
            'errors': []
        }

    def _create_l2_document(self, doc_id: str, filename: str, full_text: str) -> None:
        cypher = '''
        CREATE (d:L2_Document {
            doc_id: $doc_id,
            name: $name,
            source: $source,
            content: $content,
            node_type: 'L2_Document'
        })
        '''
        self.neo4j.execute_query(cypher, {
            'doc_id': doc_id,
            'name': filename or 'unknown',
            'source': filename or 'unknown',
            'content': full_text[:50000]
        })

    def _create_l2_entities(self, doc_id: str, entities: List[Dict]) -> int:
        if not entities:
            return 0
        cypher = '''
        MATCH (d:L2_Document {doc_id: $doc_id})
        UNWIND $entities as ent
        CREATE (e:L2_Entity {
            id: $id,
            name: ent.name,
            entity_type: ent.entity_type,
            source_evidence: ent.source_evidence,
            battery_model: ent.battery_model,
            node_type: 'L2_Entity'
        })
        CREATE (d)-[:CONTAINS]->(e)
        RETURN count(e) as cnt
        '''
        entity_data = [{
            'id': str(uuid.uuid4()),
            'name': e.get('name', ''),
            'entity_type': e.get('entity_type', 'component'),
            'source_evidence': e.get('source_evidence', ''),
            'battery_model': e.get('battery_model', '')
        } for e in entities]

        result = self.neo4j.execute_query(cypher, {'doc_id': doc_id, 'entities': entity_data})
        return result[0].get('cnt', 0) if result else 0

    def _create_l3_terms(self, doc_id: str, terms: List[Dict]) -> int:
        if not terms:
            return 0
        cypher = '''
        MATCH (d:L2_Document {doc_id: $doc_id})
        UNWIND $terms as trm
        CREATE (t:L3_Term {
            id: $id,
            term_id: trm.term_id,
            name: trm.name,
            definition: trm.definition,
            source_document_id: $doc_id,
            node_type: 'L3_Term'
        })
        CREATE (d)-[:CONTAINS]->(t)
        RETURN count(t) as cnt
        '''
        term_data = [{
            'id': str(uuid.uuid4()),
            'term_id': t.get('term_id', ''),
            'name': t.get('name', ''),
            'definition': t.get('definition', '')
        } for t in terms]

        result = self.neo4j.execute_query(cypher, {'doc_id': doc_id, 'terms': term_data})
        return result[0].get('cnt', 0) if result else 0

    def _create_cross_layer_relations(self, doc_id: str, entities: List[Dict], terms: List[Dict]) -> int:
        """Create DEFINED_AS for definition-type entities, USES_TOOL for tool-using entities."""
        relations = 0

        entity_names = {e.get('name') for e in entities if e.get('entity_type') == 'definition'}
        for term in terms:
            term_name = term.get('name', '')
            if term_name in entity_names:
                cypher = '''
                MATCH (e:L2_Entity {name: $entity_name, doc_id: $doc_id})
                MATCH (t:L3_Term {name: $term_name, source_document_id: $doc_id})
                MERGE (e)-[r:DEFINED_AS]->(t)
                RETURN count(r) as cnt
                '''
                result = self.neo4j.execute_query(cypher, {
                    'entity_name': term_name,
                    'term_name': term_name,
                    'doc_id': doc_id
                })
                relations += result[0].get('cnt', 0) if result else 0

        tool_entities = [e for e in entities if e.get('entity_type') == 'tool']
        component_entities = [e for e in entities if e.get('entity_type') == 'component']
        for comp in component_entities:
            for tool in tool_entities:
                cypher = '''
                MATCH (c:L2_Entity {name: $comp_name, doc_id: $doc_id})
                MATCH (t:L2_Entity {name: $tool_name, doc_id: $doc_id})
                MERGE (c)-[r:USES_TOOL]->(t)
                RETURN count(r) as cnt
                '''
                result = self.neo4j.execute_query(cypher, {
                    'comp_name': comp.get('name'),
                    'tool_name': tool.get('name'),
                    'doc_id': doc_id
                })
                relations += result[0].get('cnt', 0) if result else 0

        for term in terms:
            cypher = '''
            MATCH (t:L3_Term {name: $name, source_document_id: $doc_id})
            MATCH (d:L2_Document {doc_id: $doc_id})
            MERGE (t)-[r:ORIGINATED_FROM]->(d)
            RETURN count(r) as cnt
            '''
            result = self.neo4j.execute_query(cypher, {
                'name': term.get('name'),
                'doc_id': doc_id
            })
            relations += result[0].get('cnt', 0) if result else 0

        for entity in entities:
            cypher = '''
            MATCH (e:L2_Entity {name: $name, doc_id: $doc_id})
            MATCH (d:L2_Document {doc_id: $doc_id})
            MERGE (e)-[r:REFERENCED_IN]->(d)
            RETURN count(r) as cnt
            '''
            result = self.neo4j.execute_query(cypher, {
                'name': entity.get('name'),
                'doc_id': doc_id
            })
            relations += result[0].get('cnt', 0) if result else 0

        return relations
