import pytest
from src.allocator.scorer import HumanFactorScorer


def test_scorer_import():
    assert HumanFactorScorer is not None


class MockLLM:
    def generate(self, prompt):
        return '{"visibility": 0.3, "space_limit": 0.5, "object_movement": 0.2, "ergonomic_impact": 0.4, "repetitiveness": 0.1}'


def test_human_factor_scorer():
    scorer = HumanFactorScorer(MockLLM())
    result = scorer.score_human_factors('BatteryCover', 'test context')
    assert 'visibility' in result
    assert 0 <= result['visibility'] <= 1


def test_safety_factor_scorer():
    scorer = HumanFactorScorer(MockLLM())
    result = scorer.score_safety_factors('BatteryCover', 'test context')
    assert 'high_voltage' in result
    assert 0 <= result['high_voltage'] <= 1


def test_score_all():
    scorer = HumanFactorScorer(MockLLM())
    result = scorer.score_all('BatteryCover', 'test context')
    assert 'human_scores' in result
    assert 'safety_scores' in result