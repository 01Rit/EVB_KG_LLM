# tests/graphrag/test_remanufacturing_scorer.py
import pytest
from src.graphrag.remanufacturing_scorer import RemanufacturingScorer


class TestRemanufacturingScorer:
    def test_score_pathway_returns_valid_structure(self):
        scorer = RemanufacturingScorer()
        component = {'safety_level': 3, 'value_score': 0.5, 'carbon_footprint': 0.5}

        result = scorer.score_pathway(component, 'test_battery')

        assert 'recommended' in result
        assert 'confidence' in result
        assert 'scores' in result
        assert result['recommended'] in ['discard', 'recycle', 'remanufacture', 'repair', 'reuse']

    def test_high_safety_low_value_recycle(self):
        scorer = RemanufacturingScorer()
        component = {'safety_level': 1, 'value_score': 0.2, 'carbon_footprint': 0.6}

        result = scorer.score_pathway(component, 'test_battery')

        assert result['scores']['recycle'] > result['scores']['reuse']

    def test_low_safety_high_value_reuse(self):
        scorer = RemanufacturingScorer()
        component = {'safety_level': 5, 'value_score': 0.9, 'carbon_footprint': 0.2}

        result = scorer.score_pathway(component, 'test_battery')

        assert result['recommended'] == 'reuse'

    def test_score_all_steps(self):
        scorer = RemanufacturingScorer()
        steps = [
            {'component': 'upper_housing', 'safety_level': 2},
            {'component': 'cell', 'safety_level': 4}
        ]

        result = scorer.score_all_steps(steps, 'test_battery')

        assert len(result) == 2
        assert 'remanufacturing_pathway' in result[0]
        assert 'pathway_confidence' in result[0]
        assert 'pathway_scores' in result[0]