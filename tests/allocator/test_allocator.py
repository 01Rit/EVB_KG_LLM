import pytest
from src.allocator.allocator import HumanRobotAllocator, AllocationResult
from src.sequence.planner import DisassemblySequence


def test_allocator_import():
    assert HumanRobotAllocator is not None


def test_allocation_result_model():
    result = AllocationResult(
        battery_model='test',
        allocations=[{'component': 'A', 'assignee': 'human'}],
        human_count=1,
        robot_count=0,
        total_time_seconds=30
    )
    assert result.human_count == 1


class MockLLM2:
    def __init__(self):
        self.call_count = 0

    def generate(self, prompt):
        self.call_count += 1
        if '人力' in prompt or '操作难度' in prompt:
            return '{"visibility": 0.3, "space_limit": 0.5, "object_movement": 0.2, "ergonomic_impact": 0.4, "repetitiveness": 0.1}'
        else:
            return '{"high_voltage": 0.6, "chemical_risk": 0.2, "fire_explosion": 0.1, "personal_injury": 0.3}'


def test_allocate_with_mock():
    allocator = HumanRobotAllocator(MockLLM2())
    sequence = DisassemblySequence(
        battery_model='test',
        steps=[{'step': 1, 'component': 'A', 'component_name': 'Cover', 'time_seconds': 30, 'tool_required': []}],
        parallel_groups=[['A']],
        total_time_seconds=30,
        cycle_count=0
    )
    result = allocator.allocate(sequence)
    assert result.battery_model == 'test'