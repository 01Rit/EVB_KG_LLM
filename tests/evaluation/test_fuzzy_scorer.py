"""Tests for FuzzyScorer: LLM-based fuzzy condition scoring."""
import pytest
from unittest.mock import MagicMock
from src.evaluation.fuzzy_scorer import FuzzyScorer


class TestFuzzyScorer:
    @pytest.fixture
    def scorer(self):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "0.85"
        return FuzzyScorer(llm_client=mock_llm)

    def test_exact_match_returns_one(self, scorer):
        score = scorer.score("REQUIRES_CONNECTION", "螺栓连接", "螺栓连接")
        assert score == 1.0

    def test_exact_match_cached(self, scorer):
        scorer.score("REQUIRES_CONNECTION", "螺栓连接", "螺栓连接")
        score = scorer.score("REQUIRES_CONNECTION", "螺栓连接", "螺栓连接")
        assert score == 1.0
        assert scorer.llm.generate.call_count == 0

    def test_fuzzy_match_calls_llm(self, scorer):
        score = scorer.score("REQUIRES_CONNECTION", "螺栓连接", "高强度螺栓")
        assert score == 0.85
        scorer.llm.generate.assert_called_once()

    def test_fuzzy_match_cached(self, scorer):
        scorer.score("REQUIRES_CONNECTION", "螺栓连接", "高强度螺栓")
        scorer.score("REQUIRES_CONNECTION", "螺栓连接", "高强度螺栓")
        assert scorer.llm.generate.call_count == 1

    def test_llm_returns_invalid_returns_zero(self, scorer):
        scorer.llm.generate.return_value = "无法判断"
        score = scorer.score("REQUIRES_CONNECTION", "螺栓连接", "未知实体")
        assert score == 0.0

    def test_score_range_clamped(self, scorer):
        scorer.llm.generate.return_value = "1.5"
        score = scorer.score("REQUIRES_CONNECTION", "螺栓连接", "高强度螺栓")
        assert score == 1.0

        scorer.llm.generate.return_value = "-0.3"
        score = scorer.score("REQUIRES_CONNECTION", "螺栓连接", "未知实体")
        assert score == 0.0
