import pytest
from src.utils.tokenizer import encode_string_by_tiktoken, truncate_by_token_size

def test_encode_returns_list():
    result = encode_string_by_tiktoken("hello world")
    assert isinstance(result, list)
    assert len(result) > 0

def test_truncate_respects_max_tokens():
    long_text = " ".join(["word"] * 1000)
    result = truncate_by_token_size([long_text, long_text], key=lambda x: x, max_token_size=50)
    assert len(result) < 2, f"Expected truncation but got {len(result)} items"

def test_truncate_empty_list():
    result = truncate_by_token_size([], key=lambda x: x, max_token_size=100)
    assert result == []