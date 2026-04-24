from typing import Optional, List
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

    def should_trigger(self, graph: EvidenceGraph) -> bool:
        """Placeholder - always returns True for now. Task 3 will implement actual logic."""
        return True

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
        return EvidenceGraph(nodes=[], edges=[])
