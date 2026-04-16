from openai import OpenAI
from typing import Optional
import logging
import json
import hashlib

logger = logging.getLogger(__name__)

def compute_args_hash(*args) -> str:
    return hashlib.md5(str(args).encode()).hexdigest()

class LLMClient:
    def __init__(self, api_key: str, base_url: str = 'https://api.openai.com/v1',
                 model: str = 'gpt-4o', temperature: float = 0.1, max_tokens: int = 2000):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._cache = {}

    def generate(self, prompt: str, system_message: Optional[str] = None,
                 response_format: Optional[dict] = None) -> str:
        messages = []
        if system_message:
            messages.append({'role': 'system', 'content': system_message})
        messages.append({'role': 'user', 'content': prompt})

        cache_key = compute_args_hash(self.model, messages)

        if cache_key in self._cache:
            logger.info(f"Cache hit for prompt hash: {cache_key[:8]}")
            return self._cache[cache_key]

        kwargs = {
            'model': self.model,
            'messages': messages,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'timeout': 60
        }
        if response_format:
            kwargs['response_format'] = response_format

        try:
            response = self.client.chat.completions.create(**kwargs)
            result = response.choices[0].message.content
            self._cache[cache_key] = result
            return result
        except Exception as e:
            logger.error(f'LLM generation failed: {e}')
            raise

    def generate_json(self, prompt: str, schema: list[str]) -> dict:
        response_format = {'type': 'json_object', 'schema': {'properties': {}}}
        for key in schema:
            response_format['schema']['properties'][key] = {'type': 'string'}

        result = self.generate(prompt, response_format=response_format)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {'error': 'Failed to parse JSON', 'raw': result}

    def clear_cache(self):
        """Clear the response cache."""
        self._cache = {}