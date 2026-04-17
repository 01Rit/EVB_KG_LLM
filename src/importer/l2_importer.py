from src.kg.client import Neo4jClient
from src.importer.entity_extractor import EntityExtractor
from src.utils.llm_client import LLMClient
from typing import Dict, Any, List
import uuid
import logging

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 50000


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
        if len(full_text) > MAX_CONTENT_LENGTH:
            logger.warning(f"Content truncated from {len(full_text)} to {MAX_CONTENT_LENGTH} characters for doc_id {doc_id}")
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
            'content': full_text[:MAX_CONTENT_LENGTH]
        })

    def _create_l2_entities(self, doc_id: str, entities: List[Dict]) -> int:
        if not entities:
            return 0
        cypher = '''
        MATCH (d:L2_Document {doc_id: $doc_id})
        UNWIND $entities as ent
        CREATE (e:L2_Entity {
            id: ent.id,
            name: ent.name,
            entity_type: ent.entity_type,
            source_evidence: ent.source_evidence,
            battery_model: ent.battery_model,
            doc_id: $doc_id,
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
            id: trm.id,
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

        definition_entity_names = {e.get('name') for e in entities if e.get('entity_type') == 'definition'}
        definition_terms = [t for t in terms if t.get('name') in definition_entity_names]
        if definition_terms:
            cypher = '''
            MATCH (e:L2_Entity)
            MATCH (t:L3_Term)
            WHERE e.doc_id = $doc_id AND t.source_document_id = $doc_id
            AND e.entity_type = 'definition' AND e.name = t.name
            MERGE (e)-[:DEFINED_AS]->(t)
            RETURN count(*) as cnt
            '''
            result = self.neo4j.execute_query(cypher, {'doc_id': doc_id})
            relations += result[0].get('cnt', 0) if result else 0

        if terms:
            cypher = '''
            MATCH (t:L3_Term)
            MATCH (d:L2_Document {doc_id: $doc_id})
            WHERE t.source_document_id = $doc_id
            MERGE (t)-[:ORIGINATED_FROM]->(d)
            RETURN count(*) as cnt
            '''
            result = self.neo4j.execute_query(cypher, {'doc_id': doc_id})
            relations += result[0].get('cnt', 0) if result else 0

        if entities:
            cypher = '''
            MATCH (e:L2_Entity)
            MATCH (d:L2_Document {doc_id: $doc_id})
            WHERE e.doc_id = $doc_id
            MERGE (e)-[:REFERENCED_IN]->(d)
            RETURN count(*) as cnt
            '''
            result = self.neo4j.execute_query(cypher, {'doc_id': doc_id})
            relations += result[0].get('cnt', 0) if result else 0

        return relations
