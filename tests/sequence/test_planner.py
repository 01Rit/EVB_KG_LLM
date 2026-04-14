import pytest
from src.sequence.planner import SequencePlanner, DisassemblySequence


def test_planner_import():
    assert SequencePlanner is not None


def test_disassembly_sequence_model():
    seq = DisassemblySequence(
        battery_model='test-model',
        steps=[{'step': 1, 'component': 'A', 'time_seconds': 30}],
        parallel_groups=[['A']],
        total_time_seconds=30,
        cycle_count=0
    )
    assert seq.battery_model == 'test-model'
    assert len(seq.steps) == 1


def test_plan_empty_components():
    planner = SequencePlanner()
    result = planner.plan('test-model', [])
    assert result.battery_model == 'test-model'
    assert len(result.steps) == 0


def test_plan_with_components():
    planner = SequencePlanner()
    components = [
        {'id': 'A', 'name': 'Cover', 'precedence': []},
        {'id': 'B', 'name': 'Screw', 'precedence': ['A']},
    ]
    result = planner.plan('test-model', components)
    assert len(result.steps) == 2