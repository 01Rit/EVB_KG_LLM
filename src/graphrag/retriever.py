from src.kg.client import Neo4jClient, MilvusClient
from src.kg.models import EvidenceNode, EvidenceGraph
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class MultiPathRetriever:
    def __init__(self, neo4j_client: Neo4jClient, milvus_client: Optional[MilvusClient] = None):
        self.neo4j = neo4j_client
        self.milvus = milvus_client

    async def retrieve(self, intents: list[str], battery_model: str = None, top_k: int = 30) -> EvidenceGraph:
        all_nodes = []

        for intent in intents:
            component_nodes = self._retrieve_components(intent, top_k // 3)
            document_nodes = self._retrieve_documents(intent, top_k // 3)
            term_nodes = self._retrieve_terms(intent, top_k // 3)

            all_nodes.extend(component_nodes)
            all_nodes.extend(document_nodes)
            all_nodes.extend(term_nodes)

        if not all_nodes and battery_model:
            all_nodes = self.get_all_components(battery_model, top_k)

        deduplicated = self._deduplicate_nodes(all_nodes, top_k)

        subgraph = self.neo4j.get_subgraph([n.id for n in deduplicated], depth=2)
        evidence_graph = EvidenceGraph(nodes=deduplicated, edges=subgraph.get('edges', []))

        logger.info(f'ReTrieved {len(deduplicated)} unique nodes for {len(intents)} intents')
        return evidence_graph

    def _retrieve_components(self, query: str, top_k: int) -> list[EvidenceNode]:
        results = self.neo4j.search_components(query, top_k)
        return [
            EvidenceNode(
                node_type='Component',
                id=r.get('id', ''),
                name=r.get('name', ''),
                properties=r,
                text=f'Component: {r.get("name")}, Model: {r.get("battery_model")}, Tools: {r.get("tool_required")}, Safety: {r.get("safety_level")}'
            )
            for r in results
        ]

    def get_all_components(self, battery_model: str = None, top_k: int = 100) -> list[EvidenceNode]:
        results = self.neo4j.get_all_components(battery_model, top_k)
        return [
            EvidenceNode(
                node_type='Component',
                id=r.get('id', ''),
                name=r.get('name', ''),
                properties=r,
                text=f'Component: {r.get("name")}, Model: {r.get("battery_model")}, Tools: {r.get("tool_required")}, Safety: {r.get("safety_level")}'
            )
            for r in results
        ]

    def get_all_relations(self, battery_model: str = None) -> list[dict]:
        return self.neo4j.get_all_relations(battery_model)

    def _retrieve_documents(self, query: str, top_k: int) -> list[EvidenceNode]:
        results = self.neo4j.search_documents(query, top_k)
        return [
            EvidenceNode(
                node_type='Document',
                id=r.get('doc_id', ''),
                name=r.get('title', ''),
                properties=r,
                text=f'Document: {r.get("title")}, Source: {r.get("source_type")}'
            )
            for r in results
        ]

    def _retrieve_terms(self, query: str, top_k: int) -> list[EvidenceNode]:
        results = self.neo4j.search_terms(query, top_k)
        return [
            EvidenceNode(
                node_type='Term',
                id=r.get('term_id', ''),
                name=r.get('term_id', ''),
                properties=r,
                text=f'Term: {r.get("term_id")}, Definition: {r.get("definition", "")}'
            )
            for r in results
        ]

    def _deduplicate_nodes(self, nodes: list[EvidenceNode], top_k: int) -> list[EvidenceNode]:
        seen = {}
        for node in nodes:
            if node.id not in seen:
                seen[node.id] = node
        return list(seen.values())[:top_k]
