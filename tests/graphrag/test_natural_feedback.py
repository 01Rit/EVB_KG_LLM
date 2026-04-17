import pytest
from src.graphrag.natural_feedback import NaturalLanguageFeedback


@pytest.fixture
def feedback():
    from src.graphrag.retriever import MultiPathRetriever
    from src.graphrag.ranker import EvidenceRanker
    from src.utils.llm_client import LLMClient
    from src.config import settings

    neo4j = None
    milvus = None
    llm = LLMClient(api_key=settings.openai_api_key, base_url=settings.openai_base_url, model=settings.llm_model)
    retriever = MultiPathRetriever(neo4j, milvus)
    ranker = EvidenceRanker()

    return NaturalLanguageFeedback(retriever, ranker, llm)


def test_natural_feedback_import():
    assert NaturalLanguageFeedback is not None


def test_progress_stages():
    """Test that progress stages are defined"""
    assert len(NaturalLanguageFeedback.PROGRESS_STAGES) == 6
    stages = [s[0] for s in NaturalLanguageFeedback.PROGRESS_STAGES]
    assert "understanding" in stages
    assert "done" in stages


def test_generate_sync_returns_dict(feedback):
    """Test that generate_sync returns a dictionary"""
    result = feedback.generate_sync(
        question="磷酸铁锂电池有什么特点？",
        use_web_search=False
    )
    assert isinstance(result, dict)
