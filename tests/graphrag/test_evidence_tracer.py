import pytest
from src.graphrag.evidence_tracer import EvidenceTracer
from src.kg.models import EvidenceNode, EvidenceGraph


class TestEvidenceTracer:
    def test_trace_step_finds_matching_node(self):
        tracer = EvidenceTracer()
        evidence_graph = EvidenceGraph(
            nodes=[
                EvidenceNode(
                    node_type='Component',
                    id='comp_001',
                    name='upper_housing',
                    properties={'safety_level': 2},
                    relationships=[],
                    text='Upper housing component'
                )
            ],
            edges=[]
        )
        step = {'id': 1, 'component': 'upper_housing'}

        result = tracer.trace_step(step, evidence_graph)

        assert result['step_id'] == 1
        assert len(result['evidence_sources']) == 1
        assert result['evidence_sources'][0]['node_id'] == 'comp_001'
        assert result['evidence_sources'][0]['name'] == 'upper_housing'

    def test_trace_step_no_match(self):
        tracer = EvidenceTracer()
        evidence_graph = EvidenceGraph(nodes=[], edges=[])
        step = {'id': 1, 'component': 'unknown_component'}

        result = tracer.trace_step(step, evidence_graph)

        assert result['step_id'] == 1
        assert result['evidence_sources'] == []

    def test_trace_all_steps(self):
        tracer = EvidenceTracer()
        evidence_graph = EvidenceGraph(
            nodes=[
                EvidenceNode(
                    node_type='Component',
                    id='comp_001',
                    name='upper_housing',
                    properties={},
                    relationships=[],
                    text='Upper housing'
                ),
                EvidenceNode(
                    node_type='Component',
                    id='comp_002',
                    name='insulator',
                    properties={},
                    relationships=[],
                    text='Insulator'
                )
            ],
            edges=[]
        )
        steps = [
            {'id': 1, 'component': 'upper_housing'},
            {'id': 2, 'component': 'insulator'}
        ]

        result = tracer.trace_all_steps(steps, evidence_graph)

        assert len(result) == 2
        assert result[0]['evidence_sources'][0]['name'] == 'upper_housing'
        assert result[1]['evidence_sources'][0]['name'] == 'insulator'