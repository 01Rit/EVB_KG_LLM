import pytest
from src.sequence.cycle_detector import CycleDetector


def test_cycle_detector_import():
    assert CycleDetector is not None


def test_build_graph():
    detector = CycleDetector()
    components = [
        {'id': 'A', 'precedence': ['B']},
        {'id': 'B', 'precedence': []},
    ]
    graph = detector.build_graph(components)
    assert graph.number_of_nodes() == 2
    assert graph.number_of_edges() == 1


def test_detect_cycles():
    detector = CycleDetector()
    components = [
        {'id': 'A', 'precedence': ['B']},
        {'id': 'B', 'precedence': ['A']},
    ]
    detector.build_graph(components)
    cycles = detector.detect_cycles()
    assert len(cycles) > 0


def test_has_cycles():
    detector = CycleDetector()
    components = [
        {'id': 'A', 'precedence': ['B']},
        {'id': 'B', 'precedence': ['A']},
    ]
    detector.build_graph(components)
    assert detector.has_cycles() is True


def test_no_cycles():
    detector = CycleDetector()
    components = [
        {'id': 'A', 'precedence': []},
        {'id': 'B', 'precedence': ['A']},
    ]
    detector.build_graph(components)
    assert detector.has_cycles() is False


def test_break_cycles():
    detector = CycleDetector()
    components = [
        {'id': 'A', 'precedence': ['B']},
        {'id': 'B', 'precedence': ['A']},
    ]
    detector.build_graph(components)
    broken = detector.break_cycles()
    assert broken.number_of_edges() < detector.graph.number_of_edges()


def test_isolated_nodes_not_removed():
    """Isolated nodes should NOT be removed - they should be preserved as independent steps"""
    detector = CycleDetector()
    components = [
        {'id': 'A', 'precedence': []},  # isolated node (no dependencies)
        {'id': 'B', 'precedence': ['A']},
    ]
    graph = detector.build_graph(components)
    broken = detector.break_cycles()

    # A should still be in the graph as an independent step
    assert 'A' in broken.nodes(), "Isolated node 'A' was incorrectly removed"
    assert 'B' in broken.nodes()


def test_self_loop_detection():
    """Self-loops should be detected as cycles"""
    detector = CycleDetector()
    components = [
        {'id': 'A', 'precedence': ['A']},  # self-loop
    ]
    graph = detector.build_graph(components)
    cycles = detector.detect_cycles()
    assert len(cycles) > 0, "Self-loop should be detected"


def test_self_loop_break():
    """Self-loops should be broken by remove_cycle"""
    detector = CycleDetector()
    components = [
        {'id': 'A', 'precedence': ['A']},  # self-loop
    ]
    detector.build_graph(components)
    broken = detector.break_cycles()
    # After breaking self-loop, A should have no self-edge
    assert not broken.has_edge('A', 'A'), "Self-loop should be removed"


def test_empty_id_filtered():
    """Components with empty id and name should be filtered out"""
    detector = CycleDetector()
    components = [
        {'id': '', 'name': '', 'precedence': []},  # invalid
        {'id': 'A', 'precedence': []},  # valid
    ]
    graph = detector.build_graph(components)
    assert '' not in graph.nodes(), "Empty string node should not be added"
    assert 'A' in graph.nodes()


def test_dependency_to_nonexistent_filtered():
    """Dependencies to non-existent nodes should be filtered"""
    detector = CycleDetector()
    components = [
        {'id': 'A', 'precedence': ['B', 'C']},  # B and C don't exist
        {'id': 'D', 'precedence': []},
    ]
    graph = detector.build_graph(components)
    # Only D should be in the graph, no edges from A since B and C don't exist
    assert 'B' not in graph.nodes()
    assert 'C' not in graph.nodes()
    assert 'D' in graph.nodes()