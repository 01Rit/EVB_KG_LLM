import pytest
from src.graphrag.retriever import MultiPathRetriever


def test_retriever_import():
    assert MultiPathRetriever is not None