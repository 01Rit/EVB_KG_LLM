import pytest
from src.sequence.time_estimator import TimeEstimator


def test_time_estimator_import():
    assert TimeEstimator is not None


def test_calculate_time():
    estimator = TimeEstimator()
    result = estimator.calculate_time(1.0, 5, 15)
    assert result > 0


def test_calculate_time_defaults():
    estimator = TimeEstimator()
    result = estimator.calculate_time(1.0)
    assert result > 0


def test_estimate_from_component():
    estimator = TimeEstimator()
    component = {'id': 'A', 'tool_required': ['screwdriver']}
    result = estimator.estimate_from_component(component)
    assert result > 0


def test_estimate_sequence_time():
    estimator = TimeEstimator()
    components = [
        {'id': 'A', 'tool_required': ['screwdriver']},
        {'id': 'B', 'tool_required': ['wrench']},
    ]
    result = estimator.estimate_sequence_time(components)
    assert result['total_seconds'] > 0
    assert len(result['details']) == 2