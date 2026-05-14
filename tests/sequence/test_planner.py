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
    insulator = next((c for c in result if c['name'] == 'Insulator'), None)
    assert upper_housing is not None
    assert insulator is not None
    # 依赖引用被标准化为组件ID（名称 -> ID 转换）
    # head -> tail 表示 head 必须在 tail 之前拆卸，所以 tail 依赖 head
    assert 'upper_housing' in insulator['dependencies']


def test_parallel_disassembly_with_relations():
    """测试关系解析：冷却板和冷却管都依赖BMC，它们应该可并行拆卸"""
    planner = SequencePlanner()
    components_data = [
        {'id': 'bmc', 'name': 'BMC', 'precedence': [], 'tool_required': [], 'safety_level': 1},
        {'id': 'cooling_pipe', 'name': '冷却管', 'precedence': [], 'tool_required': [], 'safety_level': 1},
        {'id': 'cooling_plate', 'name': '冷却板', 'precedence': [], 'tool_required': [], 'safety_level': 1},
    ]
    relations_data = [
        {'head': 'BMC', 'tail': '冷却管', 'relation': '必须先于...拆卸'},
        {'head': 'BMC', 'tail': '冷却板', 'relation': '必须先于...拆卸'},
    ]
    result = planner._parse_components_with_relations(components_data, relations_data)

    # 验证冷却管和冷却板的依赖是 BMC
    cooling_pipe = next(c for c in result if c['name'] == '冷却管')
    cooling_plate = next(c for c in result if c['name'] == '冷却板')

    assert 'bmc' in cooling_pipe['dependencies'], f"冷却管应依赖BMC，实际: {cooling_pipe['dependencies']}"
    assert 'bmc' in cooling_plate['dependencies'], f"冷却板应依赖BMC，实际: {cooling_plate['dependencies']}"


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


def test_topo_sort_steps_have_id():
    """Test that topological sort steps include id field"""
    planner = SequencePlanner()
    components = [
        {'id': 'A', 'name': 'Cover', 'precedence': []},
        {'id': 'B', 'name': 'Screw', 'precedence': ['A']},
    ]
    result = planner.plan('test-model', components)

    assert len(result.steps) == 2
    for i, step in enumerate(result.steps, 1):
        assert 'id' in step, f"Step should have id field: {step}"
        assert step['id'] == i, f"Step id should be {i}, got: {step['id']}"