import pytest
from src.graph_output.mermaid_gen import MermaidGenerator
from src.sequence.planner import DisassemblySequence


def test_mermaid_gen_import():
    assert MermaidGenerator is not None


def test_generate_simple():
    gen = MermaidGenerator()
    sequence = DisassemblySequence(
        battery_model='test',
        steps=[{'step': 1, 'component': 'A', 'component_name': 'Cover', 'time_seconds': 30, 'tool_required': []}],
        parallel_groups=[['A']],
        total_time_seconds=30,
        cycle_count=0
    )
    result = gen.generate(sequence)
    assert 'graph TD' in result


def test_generate_parallel():
    gen = MermaidGenerator()
    groups = [['A', 'B'], ['C']]
    result = gen.generate_parallel(groups)
    assert 'graph TD' in result