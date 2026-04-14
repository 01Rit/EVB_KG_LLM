import networkx as nx
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class TopologicalSort:
    def __init__(self):
        self.graph = None

    def set_graph(self, graph: nx.DiGraph):
        self.graph = graph

    def sort(self) -> List[str]:
        if not self.graph:
            raise RuntimeError("Graph not set")

        try:
            sorted_list = list(nx.topological_sort(self.graph))
            logger.info(f"Topological sort produced {len(sorted_list)} items")
            return sorted_list
        except nx.NetworkXError as e:
            logger.error(f"Topological sort failed: {e}")
            raise

    def get_parallel_groups(self) -> List[List[str]]:
        if not self.graph:
            raise RuntimeError("Graph not set")

        inDegree = {}
        for node in self.graph.nodes():
            inDegree[node] = self.graph.in_degree(node)

        groups = []
        processed = set()

        while len(processed) < self.graph.number_of_nodes():
            current_group = []

            for node in self.graph.nodes():
                if node not in processed and inDegree[node] == 0:
                    current_group.append(node)

            if not current_group:
                break

            groups.append(current_group)

            for node in current_group:
                processed.add(node)
                for neighbor in self.graph.successors(node):
                    inDegree[neighbor] -= 1

        logger.info(f"Generated {len(groups)} parallel groups")
        return groups

    def reverse_sort(self) -> List[str]:
        if not self.graph:
            raise RuntimeError("Graph not set")

        reversed_graph = self.graph.reverse()

        try:
            sorted_list = list(nx.topological_sort(reversed_graph))
            return sorted_list
        except nx.NetworkXError as e:
            logger.error(f"Reverse topological sort failed: {e}")
            raise