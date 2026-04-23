import pytest
from unittest.mock import MagicMock, patch
from src.graphrag.community import CommunityDetector


def test_detect_communities_returns_list():
    """Test that detect returns list of community dicts."""
    mock_neo4j = MagicMock()
    mock_neo4j.detect_communities.return_value = [
        {'id': 0, 'nodes': ['A', 'B'], 'level': 2},
        {'id': 1, 'nodes': ['C', 'D'], 'level': 2}
    ]

    mock_llm = MagicMock()
    detector = CommunityDetector(mock_neo4j, mock_llm)
    communities = detector.detect()
    assert len(communities) == 2
    assert communities[0]['id'] == 0


def test_generate_report_for_community():
    """Test that generate_report returns parsed JSON."""
    mock_neo4j = MagicMock()
    mock_neo4j.get_subgraph_nodes.return_value = [
        {'id': 'A', 'props': {'name': 'Component A'}},
        {'id': 'B', 'props': {'name': 'Component B'}}
    ]

    mock_llm = MagicMock()
    mock_llm.generate.return_value = '{"title": "Test", "summary": "Test summary", "findings": []}'

    detector = CommunityDetector(mock_neo4j, mock_llm)
    community = {'id': 0, 'nodes': ['A', 'B'], 'level': 2}
    report = detector.generate_report(community)
    assert 'title' in report
    assert report['title'] == 'Test'


def test_generate_report_handles_llm_error():
    """Test that generate_report handles LLM errors gracefully."""
    mock_neo4j = MagicMock()
    mock_neo4j.get_subgraph_nodes.return_value = []

    mock_llm = MagicMock()
    mock_llm.generate.side_effect = Exception("LLM error")

    detector = CommunityDetector(mock_neo4j, mock_llm)
    community = {'id': 0, 'nodes': ['A'], 'level': 2}
    report = detector.generate_report(community)
    assert report['title'] == 'Error'


@pytest.mark.asyncio
async def test_generate_all_reports():
    """Test async generation of all community reports."""
    mock_neo4j = MagicMock()
    mock_neo4j.detect_communities.return_value = [
        {'id': 0, 'nodes': ['A', 'B'], 'level': 2}
    ]
    mock_neo4j.get_subgraph_nodes.return_value = [
        {'id': 'A', 'props': {'name': 'Component A'}}
    ]

    mock_llm = MagicMock()
    mock_llm.generate.return_value = '{"title": "Report", "summary": "Summary", "findings": []}'

    detector = CommunityDetector(mock_neo4j, mock_llm)
    communities = [{'id': 0, 'nodes': ['A', 'B'], 'level': 2}]
    reports = await detector.generate_all_reports(communities)

    assert len(reports) == 1
    assert reports[0]['community_id'] == 0
    assert reports[0]['node_count'] == 2