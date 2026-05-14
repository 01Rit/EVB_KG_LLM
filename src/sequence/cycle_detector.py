import networkx as nx
from typing import List, Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)


class CycleDetector:
    def __init__(self):
        self.graph = None

    def build_graph(self, components: List[Dict]) -> nx.DiGraph:
        graph = nx.DiGraph()

        # 收集所有有效的节点ID（使用组件ID作为图中的节点标识符）
        valid_node_ids = set()
        for comp in components:
            comp_id = comp.get('id') or comp.get('name', '')
            if comp_id and comp_id.strip():
                valid_node_ids.add(comp_id)

        # 添加节点
        for comp in components:
            comp_id = comp.get('id') or comp.get('name', '')
            if comp_id and comp_id.strip():  # 过滤空字符串
                graph.add_node(comp_id, **comp)

        # 添加边，过滤掉指向空字符串或不存在节点的边
        for comp in components:
            comp_id = comp.get('id') or comp.get('name', '')
            if not comp_id or not comp_id.strip():
                continue
            dependencies = comp.get('precedence', []) or comp.get('dependencies', [])

            for dep in dependencies:
                # 跳过空字符串和指向不存在节点的边
                if not dep or not dep.strip():
                    continue
                if dep not in valid_node_ids:
                    # 跳过指向不存在节点的边
                    continue
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
                # simple_cycles 只返回长度 >= 2 的环
                if len(cycle) >= 2:
                    cycles.append(cycle)
            # 单独检测自环（simple_cycles 不会返回长度为 1 的环）
            self_loops = self._get_self_loops()
            for node in self_loops:
                cycles.append([node])
        except nx.NetworkXError as e:
            logger.warning(f"Error detecting cycles: {e}")

        logger.info(f"Detected {len(cycles)} cycles")
        return cycles

    def _get_self_loops(self) -> set:
        """获取图中所有自环节点的集合"""
        if not self.graph:
            return set()
        return {node for node in self.graph.nodes() if self.graph.has_edge(node, node)}

    def break_cycles(self, method: str = 'remove_last') -> nx.DiGraph:
        if not self.graph:
            raise RuntimeError("Graph not built")

        broken_graph = self.graph.copy()

        # 处理多节点环（simple_cycles 不会返回自环）
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

        # 处理自环（simple_cycles 不会返回长度为 1 的环）
        self_loops = self._get_self_loops()
        for node in self_loops:
            if broken_graph.has_edge(node, node):
                broken_graph.remove_edge(node, node)
                logger.info(f"Removed self-loop on node: {node}")

        logger.info(f"Broke cycles using {method}")
        return broken_graph