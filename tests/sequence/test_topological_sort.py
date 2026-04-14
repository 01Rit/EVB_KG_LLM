import pytest
from src.sequence.topological_sort import TopologicalSort
import networkx as nx


def test_topological_sort_import():
    assert TopologicalSort is not None


def test_sort_linear():
    sorter = TopologicalSort()
    graph = nx.DiGraph()
    graph.add_edges_from([('A', 'B'), ('B', 'C')])
    sorter.set_graph(graph)
    result = sorter.sort()
    assert len(result) == 3


def test_get_parallel_groups():
    sorter = TopologicalSort()
    graph = nx.DiGraph()
    graph.add_edges_from([('A', 'C'), ('B', 'C')])
    sorter.set_graph(graph)
    groups = sorter.get_parallel_groups()
    assert len(groups) >= 2


def test_reverse_sort():
    sorter = TopologicalSort()
    graph = nx.DiGraph()
    graph.add_edges_from([('A', 'B'), ('B', 'C')])
    sorter.set_graph(graph)
    result = sorter.reverse_sort()
    assert len(result) == 3