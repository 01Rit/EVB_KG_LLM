from src.kg.client import Neo4jClient
from src.importer.entity_extractor import EntityExtractor
from src.utils.llm_client import LLMClient
from src.cross_layer.linker import CrossLayerLinker
from typing import Dict, Any, List, Optional, Callable
import uuid
import logging

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 50000


class L2Importer:
    def __init__(self, neo4j_client: Neo4jClient, llm_client: LLMClient,
                 progress_callback: Optional[Callable] = None,
                 linker: Optional[CrossLayerLinker] = None):
        self.neo4j = neo4j_client
        extraction_llm = LLMClient(
            api_key=llm_client.client.api_key,
            base_url=llm_client.client.base_url,
            model=llm_client.model,
            temperature=llm_client.temperature,
            max_tokens=4000
        )
        self.extractor = EntityExtractor(extraction_llm)
        self.progress_callback = progress_callback
        self.linker = linker

    def _report_progress(self, stage: str, current: int, total: int,
                         message: str, detail: str = None) -> None:
        if self.progress_callback:
            self.progress_callback(stage, current, total, message, detail)

    def import_pdf(self, full_text: str, filename: str) -> Dict[str, Any]:
        self._report_progress('parsing', 5, 100, '## 📄 开始解析PDF文档...')

        extraction = self.extractor.extract_entities_chunked(
            full_text, filename=filename, chunk_size=4000, overlap=100
        )
        entities = extraction.get('entities', [])
        terms = extraction.get('terms', [])

        self._report_progress('extracting', 15, 100, f'## 🔍 提取完成\n\n**实体**: {len(entities)} 个\n**术语**: {len(terms)} 个')

        doc_id = str(uuid.uuid4())
        self._create_l2_document(doc_id, filename, full_text, 'pdf')
        self._report_progress('creating_nodes', 25, 100, '## 🗄️ 创建L2文档节点...')

        entities_created = self._create_l2_entities(doc_id, entities)
        self._report_progress('creating_nodes', 45, 100, f'## ✅ 创建L2实体节点\n\n**共创建**: {entities_created} 个')

        terms_created = self._create_l3_terms(doc_id, terms)
        self._report_progress('creating_nodes', 65, 100, f'## ✅ 创建L3术语节点\n\n**共创建**: {terms_created} 个')

        relations = self._create_cross_layer_relations(doc_id, entities, terms)
        self._report_progress('creating_relations', 85, 100, f'## 🔗 创建跨层关系\n\n**共创建**: {relations} 个')

        self._report_progress('completing', 100, 100, '## ✅ L2 PDF导入流程完成')

        return {
            'doc_id': doc_id,
            'entities_created': entities_created,
            'terms_created': terms_created,
            'relations_created': relations,
            'errors': []
        }

    def import_markdown(self, full_text: str, filename: str) -> Dict[str, Any]:
        self._report_progress('parsing', 5, 100, '## 📝 开始解析Markdown文档...')

        extraction = self.extractor.extract_entities_chunked(
            full_text, filename=filename, chunk_size=4000, overlap=100
        )
        entities = extraction.get('entities', [])
        terms = extraction.get('terms', [])

        self._report_progress('extracting', 15, 100, f'## 🔍 提取完成\n\n**实体**: {len(entities)} 个\n**术语**: {len(terms)} 个')

        doc_id = str(uuid.uuid4())
        self._create_l2_document(doc_id, filename, full_text, 'markdown')
        self._report_progress('creating_nodes', 25, 100, '## 🗄️ 创建L2文档节点...')

        entities_created = self._create_l2_entities(doc_id, entities)
        self._report_progress('creating_nodes', 45, 100, f'## ✅ 创建L2实体节点\n\n**共创建**: {entities_created} 个')

        terms_created = self._create_l3_terms(doc_id, terms)
        self._report_progress('creating_nodes', 65, 100, f'## ✅ 创建L3术语节点\n\n**共创建**: {terms_created} 个')

        relations = self._create_cross_layer_relations(doc_id, entities, terms)
        self._report_progress('creating_relations', 85, 100, f'## 🔗 创建跨层关系\n\n**共创建**: {relations} 个')

        self._report_progress('completing', 100, 100, '## ✅ L2 Markdown导入流程完成')

        return {
            'doc_id': doc_id,
            'entities_created': entities_created,
            'terms_created': terms_created,
            'relations_created': relations,
            'errors': []
        }

    def _create_l2_document(self, doc_id: str, filename: str, full_text: str, source_type: str = 'pdf') -> None:
        if len(full_text) > MAX_CONTENT_LENGTH:
            logger.warning(f"Content truncated from {len(full_text)} to {MAX_CONTENT_LENGTH} characters for doc_id {doc_id}")
        cypher = '''
        CREATE (d:L2_Document {
            doc_id: $doc_id,
            name: $name,
            source: $source,
            content: $content,
            source_type: $source_type,
            node_type: 'L2_Document'
        })
        '''
        self.neo4j.execute_query(cypher, {
            'doc_id': doc_id,
            'name': filename or 'unknown',
            'source': filename or 'unknown',
            'content': full_text[:MAX_CONTENT_LENGTH],
            'source_type': source_type
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
        """Create cross-layer relations.

        Creates:
        - DEFINITION_OF (L2→L3) via linker or name matching
        - REFERENCE_OF (L1→L2) via linker
        - ORIGINATED_FROM (L3→Document)
        - REFERENCED_IN (L2→Document)
        """
        relations = 0

        if self.linker and self._is_linker_available():
            try:
                linker_relations = self._create_definition_of_via_linker(doc_id, entities, terms)
                relations += linker_relations
                logger.info(f"Created {linker_relations} DEFINITION_OF relations via linker")
            except Exception as e:
                logger.warning(f"Linker failed: {e}, using name matching fallback")

        relations += self._create_definition_of_by_name_matching(doc_id, entities, terms)

        relations += self._create_reference_of_via_linker(doc_id, entities)

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

    def _is_linker_available(self) -> bool:
        """Check if CrossLayerLinker is available (Milvus connected)."""
        if not self.linker:
            return False
        try:
            if hasattr(self.linker, 'embedder') and self.linker.embedder.milvus_client:
                if hasattr(self.linker.embedder.milvus_client, 'collection'):
                    return self.linker.embedder.milvus_client.collection is not None
            return False
        except Exception:
            return False

    def _create_definition_of_by_name_matching(self, doc_id: str, entities: List[Dict], terms: List[Dict]) -> int:
        """Create DEFINITION_OF relations by name matching as fallback."""
        if not entities or not terms:
            return 0

        entity_names = {e.get('name') for e in entities if e.get('name')}
        term_names = {t.get('name') for t in terms if t.get('name')}
        matching_names = entity_names & term_names

        if not matching_names:
            return 0

        cypher = '''
        MATCH (e:L2_Entity)
        MATCH (t:L3_Term)
        WHERE e.doc_id = $doc_id AND t.source_document_id = $doc_id
        AND e.name IN $matching_names
        MERGE (e)-[:DEFINED_AS]->(t)
        RETURN count(*) as cnt
        '''
        result = self.neo4j.execute_query(cypher, {'doc_id': doc_id, 'matching_names': list(matching_names)})
        count = result[0].get('cnt', 0) if result else 0
        logger.info(f"Created {count} DEFINITION_OF relations via name matching")
        return count

    def _create_reference_of_via_linker(self, doc_id: str, entities: List[Dict]) -> int:
        """Create REFERENCE_OF (L1→L2) relations using CrossLayerLinker."""
        if not self.linker:
            return 0

        if not self._is_linker_available():
            logger.warning("Milvus not available, skipping REFERENCE_OF via linker")
            return 0

        relations = 0
        entity_ids = self._get_l2_entity_ids(doc_id)
        entity_id_map = {e.get('name', ''): e.get('id', '') for e in entities}
        for name, new_id in entity_ids.items():
            if name in entity_id_map:
                entity_id_map[name] = new_id

        l1_components = self._get_all_l1_components()
        component_id_map = {c.get('name', ''): c.get('id', '') for c in l1_components}

        for entity in entities:
            entity_name = entity.get('name', '')
            target_id = entity_id_map.get(entity_name, '')
            if not target_id:
                continue

            source_id = component_id_map.get(entity_name, '')
            if not source_id:
                continue

            try:
                candidates = self.linker.run_pipeline(
                    source_node_id=source_id,
                    source_name=entity_name,
                    source_type='Component',
                    source_layer='L1',
                    source_context='',
                    target_layer='L2',
                    relation_type='REFERENCE_OF'
                )
                written = self.linker.write_relations(candidates, 'REFERENCE_OF')
                relations += written
            except Exception as e:
                logger.error(f"Reference_of linker failed for {entity_name}: {e}")
                continue

        logger.info(f"Created {relations} REFERENCE_OF relations via linker")
        return relations

    def _get_all_l1_components(self) -> List[Dict]:
        """Get all L1 components from Neo4j."""
        cypher = '''
        MATCH (c:Component)
        RETURN c.id as id, c.name as name
        '''
        try:
            result = self.neo4j.execute_query(cypher, {})
            return result if result else []
        except Exception:
            return []

    def _create_definition_of_via_linker(self, doc_id: str, entities: List[Dict], terms: List[Dict]) -> int:
        """Create DEFINITION_OF (L2→L3) relations using CrossLayerLinker."""
        if not self.linker:
            return 0

        if not self._is_linker_available():
            logger.warning("Milvus not available, skipping linker path")
            return 0

        relations = 0
        term_dict = {t.get('name', ''): t for t in terms}

        entity_ids = self._get_l2_entity_ids(doc_id)
        entity_id_map = {e.get('name', ''): e.get('id', '') for e in entities}
        for name, new_id in entity_ids.items():
            if name in entity_id_map:
                entity_id_map[name] = new_id

        for entity in entities:
            entity_name = entity.get('name', '')
            if entity_name not in term_dict:
                continue

            term = term_dict[entity_name]
            term_ids = self._get_l3_term_ids(doc_id)
            term_id = term_ids.get(term.get('name', ''), '')

            if not term_id:
                continue

            source_id = entity_id_map.get(entity_name, '')
            if not source_id:
                continue

            try:
                candidates = self.linker.run_pipeline(
                    source_node_id=source_id,
                    source_name=entity_name,
                    source_type=entity.get('entity_type', 'Entity'),
                    source_layer='L2',
                    source_context=entity.get('source_evidence', ''),
                    target_layer='L3',
                    relation_type='DEFINITION_OF'
                )
                written = self.linker.write_relations(candidates, 'DEFINITION_OF')
                relations += written
            except Exception as e:
                logger.error(f"Definition_of linker failed for entity {entity_name}: {e}")
                continue

        logger.info(f"Created {relations} DEFINITION_OF relations via linker")
        return relations

    def _get_l2_entity_ids(self, doc_id: str) -> Dict[str, str]:
        """Get mapping of L2 entity names to IDs for a document."""
        cypher = '''
        MATCH (e:L2_Entity {doc_id: $doc_id})
        RETURN e.name as name, e.id as id
        '''
        result = self.neo4j.execute_query(cypher, {'doc_id': doc_id})
        return {r.get('name', ''): r.get('id', '') for r in result if r.get('name')}

    def _get_l3_term_ids(self, doc_id: str) -> Dict[str, str]:
        """Get mapping of L3 term names to IDs for a document."""
        cypher = '''
        MATCH (t:L3_Term {source_document_id: $doc_id})
        RETURN t.name as name, t.id as id
        '''
        result = self.neo4j.execute_query(cypher, {'doc_id': doc_id})
        return {r.get('name', ''): r.get('id', '') for r in result if r.get('name')}
