import networkx as nx
from typing import List, Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)


class CycleDetector:
    def __init__(self):
        self.graph = None

    def build_graph(self, components: List[Dict]) -> nx.DiGraph:
        graph = nx.DiGraph()

        for comp in components:
            comp_id = comp.get('id') or comp.get('name', '')
            graph.add_node(comp_id, **comp)

        for comp in components:
            comp_id = comp.get('id') or comp.get('name', '')
            dependencies = comp.get('precedence', []) or comp.get('dependencies', [])

            for dep in dependencies:
                graph.add_edge(comp_id, dep)

        self.graph = graph
        return graph

    def find_strongly_connected_components(self) -> List[List[str]]:
        if not self.graph:
            raise RuntimeError("Graph not built")

        sccs = list(nx.strongly_connected_components(self.graph))
        sccs = [scc for scc in sccs if len(scc) > 1]

        logger.info(f"Found {len(sccs)} strongly connected components (cycles)")
        return sccs

    def has_cycles(self) -> bool:
        if not self.graph:
            raise RuntimeError("Graph not built")

        try:
            nx.find_cycle(self.graph)
            return True
        except nx.NetworkXNoCycle:
            return False

    def detect_cycles(self) -> List[List[str]]:
        if not self.graph:
            raise RuntimeError("Graph not built")

        cycles = []
        try:
            for cycle in nx.simple_cycles(self.graph):
                if len(cycle) > 1:
                    cycles.append(cycle)
        except nx.NetworkXError as e:
            logger.warning(f"Error detecting cycles: {e}")

        logger.info(f"Detected {len(cycles)} cycles")
        return cycles

    def break_cycles(self, method: str = 'remove_last') -> nx.DiGraph:
        if not self.graph:
            raise RuntimeError("Graph not built")

        broken_graph = self.graph.copy()

        cycles = list(nx.simple_cycles(broken_graph))

        for cycle in cycles:
            if len(cycle) > 1:
                if method == 'remove_last':
                    broken_graph.remove_edge(cycle[-1], cycle[0])
                elif method == 'remove_first':
                    broken_graph.remove_edge(cycle[0], cycle[1])
                elif method == 'break_all':
                    for i in range(len(cycle) - 1):
                        broken_graph.remove_edge(cycle[i], cycle[(i + 1) % len(cycle)])

        logger.info(f"Broke cycles using {method}")
        return broken_graph