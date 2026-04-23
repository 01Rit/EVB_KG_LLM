# src/graphrag/constrained_retriever.py
from src.graphrag.retriever import MultiPathRetriever
from src.graphrag.constraint_engine import ConstraintEngine
from src.kg.models import EvidenceGraph
import logging

logger = logging.getLogger(__name__)


class ConstraintAwareRetriever(MultiPathRetriever):
    def __init__(self, neo4j_client, milvus_client, constraint_engine=None):
        super().__init__(neo4j_client, milvus_client)
        self.constraint_engine = constraint_engine or ConstraintEngine(neo4j_client)

    async def retrieve(self, intents: list[str], battery_model: str, top_k: int = 30) -> EvidenceGraph:
        semantic_results = await super().retrieve(intents, battery_model, top_k)

        if not semantic_results.nodes:
            return semantic_results

        components = [
            {
                'name': n.name,
                'safety_level': n.properties.get('safety_level', 3),
                'id': n.id
            }
            for n in semantic_results.nodes
        ]

        constraints = self.constraint_engine.infer_bidirectional_constraints(
            battery_model, components
        )

        valid_subgraph = self._filter_valid_subgraph(semantic_results, constraints)

        logger.info(f'ConstraintAwareRetriever: filtered {len(semantic_results.nodes)} -> {len(valid_subgraph.nodes)} nodes')
        return valid_subgraph

    def _filter_valid_subgraph(self, evidence: EvidenceGraph, constraints: list[dict]) -> EvidenceGraph:
        if not constraints:
            return evidence

        before_graph = {}
        for c in constraints:
            if c['relation'] == 'BEFORE':
                head = c['head']
                tail = c['tail']
                if head not in before_graph:
                    before_graph[head] = set()
                before_graph[head].add(tail)

        def has_valid_order(node_names: list[str]) -> bool:
            name_to_idx = {name: i for i, name in enumerate(node_names)}
            for head, tails in before_graph.items():
                if head not in name_to_idx:
                    continue
                head_idx = name_to_idx[head]
                for tail in tails:
                    if tail in name_to_idx and name_to_idx[tail] <= head_idx:
                        return False
            return True

        node_names = [n.name for n in evidence.nodes]
        if has_valid_order(node_names):
            return evidence

        sorted_nodes = self._topological_sort(evidence.nodes, before_graph)
        valid_ids = {n.id for n in sorted_nodes}

        filtered_nodes = [n for n in evidence.nodes if n.id in valid_ids]
        filtered_edges = [
            e for e in evidence.edges
            if e.get('start') in valid_ids and e.get('end') in valid_ids
        ]

        return EvidenceGraph(nodes=filtered_nodes, edges=filtered_edges)

    def _topological_sort(self, nodes: list, before_graph: dict) -> list:
        node_map = {n.name: n for n in nodes}
        in_degree = {name: 0 for name in node_map}

        for head, tails in before_graph.items():
            for tail in tails:
                if tail in in_degree:
                    in_degree[tail] += 1

        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(node_map[current])

            if current in before_graph:
                for next_node in before_graph[current]:
                    if next_node in in_degree:
                        in_degree[next_node] -= 1
                        if in_degree[next_node] == 0:
                            queue.append(next_node)

        return result if result else list(node_map.values())