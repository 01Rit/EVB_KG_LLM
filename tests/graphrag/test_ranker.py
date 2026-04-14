import pytest
from src.graphrag.ranker import EvidenceRanker


def test_ranker_import():
    assert EvidenceRanker is not None