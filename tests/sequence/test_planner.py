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


def test_parse_components_with_relates():
    """Test that RELATES relations are properly parsed and added to dependencies"""
    planner = SequencePlanner()

    components_data = [
        {'id': 'upper_housing', 'name': 'Upper Housing', 'precedence': [], 'tool_required': [], 'safety_level': 1},
        {'id': 'insulator', 'name': 'Insulator', 'precedence': [], 'tool_required': [], 'safety_level': 1},
    ]
    relations_data = [
        {'head': 'Upper Housing', 'tail': 'Insulator', 'relation': '必须先于...拆卸'}
    ]

    result = planner._parse_components_with_relations(components_data, relations_data)

    upper_housing = next((c for c in result if c['name'] == 'Upper Housing'), None)
    assert upper_housing is not None
    assert 'Insulator' in upper_housing['dependencies']


def test_isolated_node_resolution():
    """Test that isolated nodes are resolved and kept as independent steps"""
    planner = SequencePlanner()

    components = [
        {'id': 'A', 'name': 'Upper Housing', 'precedence': [], 'dependencies': []},
        {'id': 'B', 'name': 'Lower Housing', 'precedence': [], 'dependencies': []},
        {'id': 'C', 'name': 'Cooling Pipe', 'precedence': [], 'dependencies': []},
    ]

    result = planner.plan('test', components)

    step_names = [s['component_name'] for s in result.steps]
    assert 'Cooling Pipe' in step_names