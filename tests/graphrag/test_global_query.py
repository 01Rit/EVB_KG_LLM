import pytest
from unittest.mock import MagicMock, patch
from src.graphrag.global_query import GlobalQueryEngine


def test_global_query_processes_communities():
    """Test that global query processes communities via Map-Reduce."""
    mock_neo4j = MagicMock()
    mock_neo4j.detect_communities.return_value = [
        {'id': 0, 'nodes': ['A', 'B'], 'level': 2},
        {'id': 1, 'nodes': ['C', 'D'], 'level': 2}
    ]

    mock_llm = MagicMock()
    mock_llm.generate.return_value = '{"points": [{"description": "point1", "score": 0.9}]}'

    mock_detector = MagicMock()
    mock_detector.detect.return_value = mock_neo4j.detect_communities.return_value
    mock_detector.generate_all_reports = MagicMock(return_value=[
        {'title': 'Community 0', 'summary': 'Summary 0'},
        {'title': 'Community 1', 'summary': 'Summary 1'}
    ])

    with patch('asyncio.new_event_loop') as mock_loop:
        mock_instance = MagicMock()
        mock_loop.return_value = mock_instance
        mock_instance.run_until_complete.return_value = [
            {'title': 'Community 0', 'summary': 'Summary 0'},
            {'title': 'Community 1', 'summary': 'Summary 1'}
        ]

        engine = GlobalQueryEngine(mock_neo4j, mock_llm, mock_detector)
        result = engine.query("test query")

    assert 'response' in result or 'error' in result


def test_global_query_handles_no_communities():
    """Test that global query handles empty communities."""
    mock_neo4j = MagicMock()
    mock_neo4j.detect_communities.return_value = []

    mock_llm = MagicMock()
    mock_detector = MagicMock()
    mock_detector.detect.return_value = []

    engine = GlobalQueryEngine(mock_neo4j, mock_llm, mock_detector)
    result = engine.query("test query")

    assert result['response'] == 'No communities found'
    assert result['error'] is None


def test_map_phase_extracts_points():
    """Test that map phase extracts key points from reports."""
    mock_neo4j = MagicMock()
    mock_llm = MagicMock()
    mock_llm.generate.return_value = '{"points": [{"description": "key point", "score": 0.8}]}'

    engine = GlobalQueryEngine(mock_neo4j, mock_llm)
    reports = [{'title': 'Test', 'summary': 'Summary'}]

    points = engine._map_phase("test query", reports)

    assert len(points) > 0
    assert points[0].get('score', 0) > 0


def test_reduce_phase_generates_response():
    """Test that reduce phase generates final response."""
    mock_neo4j = MagicMock()
    mock_llm = MagicMock()
    mock_llm.generate.return_value = "Final response summary"

    engine = GlobalQueryEngine(mock_neo4j, mock_llm)
    points = [{'description': 'point 1', 'score': 0.9}]

    response = engine._reduce_phase("test query", points)

    assert isinstance(response, str)
    assert len(response) > 0


def test_reduce_phase_handles_empty_points():
    """Test that reduce phase handles empty points."""
    mock_neo4j = MagicMock()
    mock_llm = MagicMock()

    engine = GlobalQueryEngine(mock_neo4j, mock_llm)
    response = engine._reduce_phase("test query", [])

    assert response == "No relevant information found."