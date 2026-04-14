from src.utils.llm_client import LLMClient
from typing import Optional
import logging
import json
import re

logger = logging.getLogger(__name__)


class QueryRewriter:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
    
    def rewrite(self, original_query: str, context: Optional[list[str]] = None) -> list[str]:
        context_str = ', '.join(context) if context else '无'
        
        prompt = f'''用户查询: {original_query}
上下文: {context_str}

将查询重写为3-5个独立的检索意图，每个意图应包含:
- 核心实体（部件/工具/文档）
- 检索目标（拆卸步骤/安全要求/技术参数）

返回JSON数组格式，只返回数组，不要其他内容。'''

        try:
            result = self.llm.generate(prompt)
            intents = self._parse_intents(result)
            logger.info(f'Rewrote query into {len(intents)} intents')
            return intents
        except Exception as e:
            logger.warning(f'Query rewriting failed, using original: {e}')
            return [original_query]
    
    def _parse_intents(self, response: str) -> list[str]:
        response = response.strip()
        
        if response.startswith('['):
            try:
                intents = json.loads(response)
                if isinstance(intents, list):
                    return [str(i) for i in intents]
            except json.JSONDecodeError:
                pass
        
        lines = response.split('\n')
        intents = []
        for line in lines:
            line = line.strip()
            line = re.sub(r'^[\"-]\s*', '', line)
            line = re.sub(r'^\d+\.\s*', '', line)
            if line and len(line) > 3:
                intents.append(line)
        
        return intents[:5] if intents else [response]
