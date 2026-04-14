import pytest
from src.graph_output.generator import GraphOutputGenerator, GraphOutput
from src.sequence.planner import DisassemblySequence


def test_generator_import():
    assert GraphOutputGenerator is not None


def test_graph_output_model():
    output = GraphOutput(
        mermaid="graph TD\\n    A[...]",
        graph_json={'nodes': [], 'edges': []}
    )
    assert output.mermaid.startswith('graph TD')


def test_generate():
    gen = GraphOutputGenerator()
    sequence = DisassemblySequence(
        battery_model='test',
        steps=[{'step': 1, 'component': 'A', 'component_name': 'Cover', 'time_seconds': 30, 'safety_level': 1, 'tool_required': []}],
        parallel_groups=[['A']],
        total_time_seconds=30,
        cycle_count=0
    )
    result = gen.generate(sequence)
    assert 'graph TD' in result.mermaid
    assert result.graph_json['battery_model'] == 'test'