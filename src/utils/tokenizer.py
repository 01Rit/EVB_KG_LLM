import tiktoken
from typing import Callable, Any

ENCODER = None

def encode_string_by_tiktoken(content: str, model_name: str = "gpt-4o") -> list[int]:
    global ENCODER
    if ENCODER is None:
        ENCODER = tiktoken.encoding_for_model(model_name)
    return ENCODER.encode(content)

def truncate_by_token_size(list_data: list, key: Callable[[Any], str], max_token_size: int) -> list:
    tokens = 0
    for i, data in enumerate(list_data):
        tokens += len(encode_string_by_tiktoken(key(data)))
        if tokens > max_token_size:
            return list_data[:i]
    return list_data