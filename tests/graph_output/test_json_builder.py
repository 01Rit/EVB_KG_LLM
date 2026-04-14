import pytest
from src.graph_output.json_builder import JSONBuilder
from src.sequence.planner import DisassemblySequence


def test_json_builder_import():
    assert JSONBuilder is not None


def test_build_simple():
    builder = JSONBuilder()
    sequence = DisassemblySequence(
        battery_model='test',
        steps=[{'step': 1, 'component': 'A', 'component_name': 'Cover', 'time_seconds': 30, 'safety_level': 1, 'tool_required': []}],
        parallel_groups=[['A']],
        total_time_seconds=30,
        cycle_count=0
    )
    result = builder.build(sequence)
    assert result['battery_model'] == 'test'
    assert len(result['nodes']) == 1


def test_build_with_allocations():
    builder = JSONBuilder()
    sequence = DisassemblySequence(
        battery_model='test',
        steps=[{'step': 1, 'component': 'A', 'component_name': 'Cover', 'time_seconds': 30, 'safety_level': 1, 'tool_required': []}],
        parallel_groups=[['A']],
        total_time_seconds=30,
        cycle_count=0
    )
    allocations = [{'component': 'A', 'assignee': 'robot'}]
    result = builder.build(sequence, allocations)
    assert result['nodes'][0]['assignee'] == 'robot'