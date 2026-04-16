import pytest
from unittest.mock import patch, MagicMock
from src.utils.llm_client import LLMClient

def test_caching_returns_same_result_for_same_prompt():
    client = LLMClient(api_key="test", model="gpt-4o")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="cached response"))]

    with patch.object(client.client.chat.completions, 'create', return_value=mock_response) as mock_create:
        result1 = client.generate("test prompt")
        result2 = client.generate("test prompt")
        assert result1 == result2
        assert mock_create.call_count == 1  # second call uses cache

def test_different_prompts_call_api():
    client = LLMClient(api_key="test", model="gpt-4o")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="response"))]

    with patch.object(client.client.chat.completions, 'create', return_value=mock_response) as mock_create:
        client.generate("prompt A")
        client.generate("prompt B")
        assert mock_create.call_count == 2