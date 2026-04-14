from src.kg.models import EvidenceNode
import logging

logger = logging.getLogger(__name__)


class EvidenceRanker:
    def __init__(self, text_weight: float = 0.5, graph_weight: float = 0.3, recency_weight: float = 0.2):
        self.text_weight = text_weight
        self.graph_weight = graph_weight
        self.recency_weight = recency_weight
    
    def rank(self, nodes: list[EvidenceNode], query: str) -> list[EvidenceNode]:
        scored = []
        
        for node in nodes:
            text_score = self._calculate_text_score(node, query)
            graph_score = self._calculate_graph_score(node)
            recency_score = self._calculate_recency_score(node)
            
            final_score = (
                self.text_weight * text_score +
                self.graph_weight * graph_score +
                self.recency_weight * recency_score
            )
            
            scored.append((node, final_score))
        
        sorted_nodes = sorted(scored, key=lambda x: x[1], reverse=True)
        ranked = [node for node, score in sorted_nodes]
        
        logger.info(f'Ranked {len(ranked)} evidence nodes')
        return ranked
    
    def _calculate_text_score(self, node: EvidenceNode, query: str) -> float:
        query_lower = query.lower()
        text_lower = node.text.lower()
        
        if query_lower in text_lower:
            return 1.0
        
        query_words = set(query_lower.split())
        text_words = set(text_lower.split())
        overlap = len(query_words & text_words)
        
        return min(overlap / max(len(query_words), 1), 1.0)
    
    def _calculate_graph_score(self, node: EvidenceNode) -> float:
        degree = len(node.relationships) if node.relationships else 0
        return min(degree / 10.0, 1.0)
    
    def _calculate_recency_score(self, node: EvidenceNode) -> float:
        return node.properties.get('recency_score', 0.8)