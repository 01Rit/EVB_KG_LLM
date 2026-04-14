from src.kg.client import Neo4jClient, MilvusClient
from src.kg.models import EvidenceNode, EvidenceGraph
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class MultiPathRetriever:
    def __init__(self, neo4j_client: Neo4jClient, milvus_client: Optional[MilvusClient] = None):
        self.neo4j = neo4j_client
        self.milvus = milvus_client
    
    async def retrieve(self, intents: list[str], top_k: int = 30) -> EvidenceGraph:
        all_nodes = []
        
        for intent in intents:
            component_nodes = self._retrieve_components(intent, top_k // 3)
            document_nodes = self._retrieve_documents(intent, top_k // 3)
            term_nodes = self._retrieve_terms(intent, top_k // 3)
            
            all_nodes.extend(component_nodes)
            all_nodes.extend(document_nodes)
            all_nodes.extend(term_nodes)
        
        deduplicated = self._deduplicate_nodes(all_nodes, top_k)
        
        subgraph = self.neo4j.get_subgraph([n.id for n in deduplicated], depth=2)
        evidence_graph = EvidenceGraph(nodes=deduplicated, edges=subgraph.get('edges', []))
        
        logger.info(f'Retrieved {len(deduplicated)} unique nodes for {len(intents)} intents')
        return evidence_graph
    
    def _retrieve_components(self, query: str, top_k: int) -> list[EvidenceNode]:
        results = self.neo4j.search_components(query, top_k)
        return [
            EvidenceNode(
                node_type='Component',
                id=r.get('id', ''),
                name=r.get('name', ''),
                properties=r,
                text=f'部件: {r.get("name")}, 适用型号: {r.get("battery_model")}, 工具: {r.get("tool_required")}, 安全等级: {r.get("safety_level")}'
            )
            for r in results
        ]
    
    def _retrieve_documents(self, query: str, top_k: int) -> list[EvidenceNode]:
        results = self.neo4j.search_documents(query, top_k)
        return [
            EvidenceNode(
                node_type='Document',
                id=r.get('doc_id', ''),
                name=r.get('title', ''),
                properties=r,
                text=f'文档: {r.get("title")}, 来源: {r.get("source")}, 类型: {r.get("source_type")}\n{r.get("content", "")[:200]}'
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
                text=f'术语: {r.get("term_id")}, 定义: {r.get("definition")}, 单位: {r.get("units")}'
            )
            for r in results
        ]
    
    def _deduplicate_nodes(self, nodes: list[EvidenceNode], top_k: int) -> list[EvidenceNode]:
        seen = {}
        for node in nodes:
            if node.id not in seen:
                seen[node.id] = node
        
        return list(seen.values())[:top_k]