from src.importer.path_classifier import PathClassifier
from src.importer.pdf_parser import PDFParser
from src.importer.entity_extractor import EntityExtractor
from src.kg.client import Neo4jClient
from src.utils.llm_client import LLMClient
from typing import Optional, Dict, Any, List
import logging
import uuid

logger = logging.getLogger(__name__)


class ImportResult:
    def __init__(self, success: bool, doc_id: str = '', message: str = '', components: int = 0, terms: int = 0):
        self.success = success
        self.doc_id = doc_id
        self.message = message
        self.components = components
        self.terms = terms


class DataImporter:
    def __init__(self, neo4j_client: Neo4jClient, llm_client: LLMClient):
        self.neo4j = neo4j_client
        self.classifier = PathClassifier()
        self.parser = PDFParser()
        self.extractor = EntityExtractor(llm_client)

    def import_pdf(self, file_path: str) -> ImportResult:
        classification = self.classifier.classify(file_path)
        file_metadata = self.classifier.get_metadata(file_path)

        try:
            parsed = self.parser.parse(file_path)
        except Exception as e:
            logger.error(f"PDF parsing failed: {e}")
            return ImportResult(False, message=str(e))

        doc_id = str(uuid.uuid4())

        try:
            components = self.extractor.extract_components(parsed['full_text'])
            terms = self.extractor.extract_terms(parsed['full_text'])
        except Exception as e:
            logger.warning(f"Entity extraction failed: {e}")
            components = []
            terms = []

        self._save_to_graph(doc_id, classification, file_metadata, parsed, components, terms)

        return ImportResult(
            success=True,
            doc_id=doc_id,
            components=len(components),
            terms=len(terms)
        )

    def _save_to_graph(self, doc_id: str, classification: Dict, file_metadata: Dict,
                      parsed: Dict, components: List[Dict], terms: List[Dict]):
        cypher = '''
        CREATE (d:Document {
            doc_id: $doc_id,
            title: $title,
            source: $source,
            source_type: $source_type,
            content: $content,
            file_path: $file_path,
            metadata: $metadata
        })
        '''

        self.neo4j.execute_query(cypher, {
            'doc_id': doc_id,
            'title': file_metadata['file_name'],
            'source': classification['source'],
            'source_type': classification['source_type'],
            'content': parsed['full_text'][:50000],
            'file_path': parsed['file_path'],
            'metadata': str(file_metadata)
        })

        for comp in components:
            self._create_component(doc_id, comp)

        for term in terms:
            self._create_term(doc_id, term)

    def _create_component(self, doc_id: str, component: Dict):
        cypher = '''
        MATCH (d:Document {doc_id: $doc_id})
        CREATE (c:Component {
            id: $id,
            name: $name,
            category: $category,
            tool_required: $tools,
            safety_level: $safety,
            source_doc_id: $doc_id
        })
        CREATE (d)-[:CONTAINS]->(c)
        '''

        self.neo4j.execute_query(cypher, {
            'id': str(uuid.uuid4()),
            'name': component.get('name', ''),
            'category': component.get('category', ''),
            'tools': str(component.get('tools', [])),
            'safety': component.get('safety_level', 1),
            'doc_id': doc_id
        })

    def _create_term(self, doc_id: str, term: Dict):
        cypher = '''
        MATCH (d:Document {doc_id: $doc_id})
        CREATE (t:Term {
            term_id: $term_id,
            definition: $definition,
            units: $units,
            source_doc_id: $doc_id
        })
        CREATE (d)-[:CONTAINS]->(t)
        '''

        self.neo4j.execute_query(cypher, {
            'term_id': term.get('term_id', ''),
            'definition': term.get('definition', ''),
            'units': term.get('units'),
            'doc_id': doc_id
        })

    def promote_to_component(self, doc_id: str, component_data: Dict) -> bool:
        cypher = '''
        MATCH (d:Document {doc_id: $doc_id})
        SET d.source_type = 'manual'
        CREATE (c:Component {
            id: $id,
            name: $name,
            battery_model: $battery_model,
            tool_required: $tools,
            safety_level: $safety,
            source_type: 'manual',
            precedence: $precedence
        })
        CREATE (d)-[:PROMOTED_TO]->(c)
        RETURN c
        '''

        try:
            result = self.neo4j.execute_query(cypher, {
                'doc_id': doc_id,
                'id': str(uuid.uuid4()),
                'name': component_data.get('name', ''),
                'battery_model': component_data.get('battery_model', ''),
                'tools': str(component_data.get('tool_required', [])),
                'safety': component_data.get('safety_level', 1),
                'precedence': str(component_data.get('precedence', []))
            })
            return len(result) > 0
        except Exception as e:
            logger.error(f"Promotion failed: {e}")
            return False
