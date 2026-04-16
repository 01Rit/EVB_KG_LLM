import tiktoken
from typing import Callable, Any, Optional

ENCODER: Optional[tiktoken.Encoding] = None


def encode_string_by_tiktoken(content: str, model_name: str = "gpt-4o") -> list[int]:
    """Encode string to token IDs using tiktoken."""
    global ENCODER
    if ENCODER is None:
        try:
            ENCODER = tiktoken.encoding_for_model(model_name)
        except KeyError:
            ENCODER = tiktoken.get_encoding("cl100k_base")
    return ENCODER.encode(content)


def tokens_to_text(tokens: list[int], model_name: str = "gpt-4o") -> str:
    """Decode token IDs back to string."""
    global ENCODER
    if ENCODER is None:
        try:
            ENCODER = tiktoken.encoding_for_model(model_name)
        except KeyError:
            ENCODER = tiktoken.get_encoding("cl100k_base")
    return ENCODER.decode(tokens)


def truncate_by_token_size(list_data: list, key: Callable[[Any], str], max_token_size: int) -> list:
    """Truncate list of items by total token size of their key function output."""
    if not list_data:
        return []
    tokens = 0
    for i, data in enumerate(list_data):
        token_count = len(encode_string_by_tiktoken(key(data)))
        if tokens + token_count > max_token_size:
            if i == 0:
                return [list_data[0]]
            return list_data[:i]
        tokens += token_count
    return list_data