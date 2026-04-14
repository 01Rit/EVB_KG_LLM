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