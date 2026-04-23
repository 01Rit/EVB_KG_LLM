# tests/graphrag/test_enhanced_planner_integration.py
import pytest
from src.graphrag.evidence_tracer import EvidenceTracer
from src.graphrag.constraint_engine import ConstraintEngine
from src.graphrag.remanufacturing_scorer import RemanufacturingScorer
from src.kg.models import EvidenceNode, EvidenceGraph


class TestEvidenceTracerIntegration:
    def test_trace_step_adds_evidence_sources(self):
        """Test that EvidenceTracer correctly adds evidence_sources to steps"""
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

        assert 'evidence_sources' in result
        assert len(result['evidence_sources']) == 1
        assert result['evidence_sources'][0]['name'] == 'upper_housing'


class TestConstraintEngineIntegration:
    def test_infer_constraints_with_components(self):
        """Test that ConstraintEngine correctly infers BEFORE constraints"""
        engine = ConstraintEngine()
        components = [
            {'name': 'upper_housing', 'safety_level': 1},
            {'name': 'cell', 'safety_level': 5}
        ]

        constraints = engine.infer_bidirectional_constraints('test_battery', components)
        before_pairs = [(c['head'], c['tail']) for c in constraints if c['relation'] == 'BEFORE']

        assert ('upper_housing', 'cell') in before_pairs


class TestRemanufacturingScorerIntegration:
    def test_score_pathway_structure(self):
        """Test that RemanufacturingScorer returns correct structure"""
        scorer = RemanufacturingScorer()
        component = {'safety_level': 3, 'value_score': 0.5, 'carbon_footprint': 0.5}

        result = scorer.score_pathway(component, 'test_battery')

        assert 'recommended' in result
        assert 'confidence' in result
        assert 'scores' in result
        assert result['recommended'] in ['discard', 'recycle', 'remanufacture', 'repair', 'reuse']

    def test_high_value_component_reuse(self):
        """Test that high value components get reuse recommendation"""
        scorer = RemanufacturingScorer()
        component = {'safety_level': 5, 'value_score': 0.9, 'carbon_footprint': 0.2}

        result = scorer.score_pathway(component, 'test_battery')

        assert result['recommended'] == 'reuse'


class TestSchemaIntegration:
    def test_step_has_all_new_fields(self):
        """Test that Step schema has all new fields from Phase 1-3"""
        from src.api.schemas import Step

        step_data = {
            'id': 1,
            'component': 'test_component',
            'action': 'remove',
            'evidence_sources': [
                {'node_id': 'n1', 'node_type': 'Component', 'name': 'test'}
            ],
            'remanufacturing_pathway': 'reuse',
            'pathway_confidence': 0.85,
            'pathway_scores': {'reuse': 0.85, 'recycle': 0.3}
        }

        step = Step(**step_data)
        assert step.evidence_sources[0].name == 'test'
        assert step.remanufacturing_pathway == 'reuse'
        assert step.pathway_confidence == 0.85