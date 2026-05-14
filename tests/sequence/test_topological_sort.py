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


def test_topological_sort_parallel_groups():
    """测试：BMC -> 冷却板，BMC -> 冷却管，冷却板和冷却管应并行"""
    from src.sequence.topological_sort import TopologicalSort
    import networkx as nx

    graph = nx.DiGraph()
    # BMC -> 冷却板 (BMC先于冷却板)
    # BMC -> 冷却管 (BMC先于冷却管)
    graph.add_edge('bmc', 'cooling_plate')
    graph.add_edge('bmc', 'cooling_pipe')

    sorter = TopologicalSort()
    sorter.set_graph(graph)

    sorted_ids = sorter.sort()
    groups = sorter.get_parallel_groups()

    # 验证排序：BMC 应该在冷却板和冷却管之前
    bmc_idx = sorted_ids.index('bmc')
    cooling_plate_idx = sorted_ids.index('cooling_plate')
    cooling_pipe_idx = sorted_ids.index('cooling_pipe')

    assert bmc_idx < cooling_plate_idx, "BMC应在冷却板之前"
    assert bmc_idx < cooling_pipe_idx, "BMC应在冷却管之前"

    # 验证并行组：[[bmc], [cooling_plate, cooling_pipe]]
    assert len(groups) == 2, f"应有2个并行组，实际: {groups}"
    assert groups[0] == ['bmc'], f"第1组应为[bmc]，实际: {groups[0]}"
    assert set(groups[1]) == {'cooling_plate', 'cooling_pipe'}, f"第2组应为[cooling_plate, cooling_pipe]，实际: {groups[1]}"