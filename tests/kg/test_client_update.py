import pytest
from unittest.mock import MagicMock, patch
from src.kg.client import Neo4jClient


def test_update_component_properties():
    client = Neo4jClient('bolt://localhost:7687', 'neo4j', 'password')
    assert hasattr(client, 'update_component_properties')
    
    with patch.object(client, 'execute_query') as mock_execute:
        mock_execute.return_value = [{'c': {'name': 'test'}}]
        result = client.update_component_properties('test', {'key': 'value'})
        assert result is True
        mock_execute.assert_called_once()