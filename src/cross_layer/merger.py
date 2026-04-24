from typing import Dict, List, Optional
from src.kg.models import EvidenceGraph, EvidenceNode


class CrossLayerMerger:
    def __init__(self):
        pass

    def merge(
        self,
        original_graph: EvidenceGraph,
        cross_layer_nodes: List[EvidenceNode],
        cross_layer_edges: List[Dict],
        max_nodes: int = 100
    ) -> EvidenceGraph:
        merged_graph = EvidenceGraph(nodes=list(original_graph.nodes), edges=list(original_graph.edges))
        
        existing_ids = {n.id for n in merged_graph.nodes}
        for node in cross_layer_nodes:
            if node.id not in existing_ids:
                merged_graph.nodes.append(node)
                existing_ids.add(node.id)
        
        existing_edges = set()
        for edge in merged_graph.edges:
            edge_key = (edge.get("source"), edge.get("target"), edge.get("type"))
            existing_edges.add(edge_key)
        
        for edge in cross_layer_edges:
            edge_key = (edge.get("source"), edge.get("target"), edge.get("type"))
            if edge_key not in existing_edges:
                merged_graph.edges.append(edge)
                existing_edges.add(edge_key)
        
        if len(merged_graph.nodes) > max_nodes:
            merged_graph.nodes = merged_graph.nodes[:max_nodes]
        
        return merged_graph