import pytest
from src.graphrag.query_rewriter import QueryRewriter


def test_query_rewriter_import():
    assert QueryRewriter is not None


def test_rewriter_initialization():
    class MockLLM:
        def generate(self, prompt, **kwargs):
            return '["意图1", "意图2", "意图3"]'
    
    rewriter = QueryRewriter(MockLLM())
    assert rewriter.llm is not None
