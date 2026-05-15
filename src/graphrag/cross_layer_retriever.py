from typing import Optional, List, Set
from src.cross_layer.linker import CrossLayerLinker
from src.kg.client import Neo4jClient, MilvusClient
from src.utils.llm_client import LLMClient
from src.kg.models import EvidenceGraph, EvidenceNode
import logging

logger = logging.getLogger(__name__)


class CrossLayerRetriever:
    def __init__(
        self,
        neo4j_client: Neo4jClient,
        milvus_client: Optional[MilvusClient] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        self.linker = CrossLayerLinker(neo4j_client, milvus_client, llm_client)

    def should_trigger(self, graph: EvidenceGraph, intents: Optional[List[str]] = None) -> bool:
        """
        Returns True if ANY of three conditions is met:
        1. Minimum evidence: fewer than 5 nodes
        2. Coverage: key concepts from intents are missing from graph (< 30%)
        3. Structure completeness: graph has few edges (sparse, < 50% edge-to-node ratio)
        """
        if len(graph.nodes) < 5:
            return True

        if intents:
            key_terms = self._extract_key_terms(intents)
            coverage = self._calculate_coverage(key_terms, graph)
            if coverage < 0.3:
                return True

        if len(graph.edges) < len(graph.nodes) * 0.5:
            return True

        return False

    def _extract_key_terms(self, intents: List[str]) -> Set[str]:
        """Extract key technical terms from intents."""
        stop_words = {'拆卸', '拆解', '如何', '怎么', '什么', '请', '给', '的', '是', '在', '了', '和', '与'}
        terms = set()
        for intent in intents:
            words = intent.replace('拆卸', '').replace('拆解', '').split()
            for w in words:
                if w and w not in stop_words and len(w) > 1:
                    terms.add(w)
        return terms

    def _calculate_coverage(self, key_terms: Set[str], graph: EvidenceGraph) -> float:
        """Calculate what fraction of key terms appear in graph node names/texts."""
        if not key_terms:
            return 1.0
        covered = 0
        for term in key_terms:
            for node in graph.nodes:
                if term in node.name or term in node.text:
                    covered += 1
                    break
        return covered / len(key_terms)

    def retrieve_cross_layer(
        self,
        battery_model: str,
        intents: List[str],
    ) -> EvidenceGraph:
        """
        Retrieve cross-layer relations for given intents.
        This runs the cross_layer pipeline and returns an EvidenceGraph.
        """
        relations_written = 0
        for intent in intents:
            l1_components = self.linker.neo4j.search_components(intent, top_k=10)
            for comp in l1_components:
                refs = self.linker.run_pipeline(
                    source_node_id=comp.get('id', ''),
                    source_name=comp.get('name', ''),
                    source_type='Component',
                    source_layer='L1',
                    source_context=comp.get('battery_model', ''),
                    target_layer='L2',
                    relation_type='REFERENCE_OF',
                )
                relations_written += self.linker.write_relations(refs, 'REFERENCE_OF')
                
                l2_entities = self.linker.neo4j.search_l2_entities(comp.get('name', ''), top_k=5)
                for entity in l2_entities:
                    defs = self.linker.run_pipeline(
                        source_node_id=entity.get('id', ''),
                        source_name=entity.get('name', ''),
                        source_type=entity.get('entity_type', 'Entity'),
                        source_layer='L2',
                        source_context=entity.get('source_evidence', ''),
                        target_layer='L3',
                        relation_type='DEFINITION_OF',
                    )
                    relations_written += self.linker.write_relations(defs, 'DEFINITION_OF')
        
        logger.info(f"Cross-layer relations written: {relations_written}")

        cypher = '''
        MATCH (s)-[r:REFERENCE_OF|DEFINITION_OF]->(t)
        WHERE s.battery_model = $model OR s.battery_model IS NULL
        RETURN s.id as source_id, s.name as source_name, s.battery_model as source_context,
               type(r) as relation_type, t.id as target_id, t.name as target_name,
               t.entity_type as target_type, t.source_evidence as target_evidence
        LIMIT 200
        '''
        results = self.linker.neo4j.execute_query(cypher, {'model': battery_model})

        nodes_map = {}
        edges = []
        for row in results:
            source_id = row.get('source_id', '')
            source_name = row.get('source_name', '')
            source_context = row.get('source_context', '')
            target_id = row.get('target_id', '')
            target_name = row.get('target_name', '')
            target_type = row.get('target_type', 'Entity')
            target_evidence = row.get('target_evidence', '')
            relation_type = row.get('relation_type', '')

            if source_id and source_id not in nodes_map:
                nodes_map[source_id] = EvidenceNode(
                    node_type='Component',
                    id=source_id,
                    name=source_name,
                    properties={'battery_model': source_context},
                    relationships=[relation_type],
                    text=f"{source_name} (Component)",
                    evidence_ids=[],
                )

            if target_id and target_id not in nodes_map:
                nodes_map[target_id] = EvidenceNode(
                    node_type=target_type,
                    id=target_id,
                    name=target_name,
                    properties={'source_evidence': target_evidence},
                    relationships=[],
                    text=f"{target_name} ({target_type})",
                    evidence_ids=[],
                )

            if source_id and target_id:
                edges.append({
                    'start': source_id,
                    'end': target_id,
                    'type': relation_type,
                    'properties': {},
                })

        return EvidenceGraph(nodes=list(nodes_map.values()), edges=edges)
