import pytest
from unittest.mock import patch, MagicMock
from src.utils.llm_client import LLMClient, compute_args_hash


class TestComputeArgsHash:
    def test_same_args_produce_same_hash(self):
        hash1 = compute_args_hash("prompt1", "system1", None)
        hash2 = compute_args_hash("prompt1", "system1", None)
        assert hash1 == hash2

    def test_different_args_produce_different_hash(self):
        hash1 = compute_args_hash("prompt1", "system1", None)
        hash2 = compute_args_hash("prompt2", "system1", None)
        assert hash1 != hash2

    def test_order_matters(self):
        hash1 = compute_args_hash("prompt1", "system1")
        hash2 = compute_args_hash("system1", "prompt1")
        assert hash1 != hash2


class TestLLMClientCaching:
    @pytest.fixture
    def mock_client(self):
        with patch('src.utils.llm_client.OpenAI') as mock:
            mock_instance = MagicMock()
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "cached response"
            mock_instance.chat.completions.create.return_value = mock_response
            mock.return_value = mock_instance
            yield mock

    @pytest.fixture
    def client(self, mock_client):
        return LLMClient(api_key="test-key", model="gpt-4o")

    def test_cache_stores_result(self, client):
        result = client.generate("test prompt")
        assert len(client._cache) == 1
        assert result == "cached response"

    def test_cache_returns_cached_result(self, client):
        client.generate("test prompt")
        result2 = client.generate("test prompt")
        assert client.client.chat.completions.create.call_count == 1
        assert result2 == "cached response"

    def test_different_prompts_different_cache_entries(self, client):
        client.generate("prompt1")
        client.generate("prompt2")
        assert len(client._cache) == 2

    def test_clear_cache(self, client):
        client.generate("test prompt")
        assert len(client._cache) == 1
        client.clear_cache()
        assert len(client._cache) == 0

    def test_cache_key_includes_system_message(self, client):
        client.generate("prompt", system_message="system1")
        assert len(client._cache) == 1
        client.clear_cache()
        client.generate("prompt", system_message="system2")
        assert len(client._cache) == 1

    def test_cache_key_includes_response_format(self, client):
        client.generate("prompt", response_format={"type": "json_object"})
        assert len(client._cache) == 1
        client.clear_cache()
        client.generate("prompt", response_format={"type": "text"})
        assert len(client._cache) == 1
