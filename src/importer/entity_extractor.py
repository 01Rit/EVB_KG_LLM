from src.utils.llm_client import LLMClient
from typing import Dict, List, Any, Optional
import logging
import json
import re

logger = logging.getLogger(__name__)


class EntityExtractor:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def extract_components(self, text: str, max_items: int = 50) -> List[Dict[str, Any]]:
        prompt = f'''从以下技术文档中提取所有可拆卸部件（L2层Document）。

提取要求：
- 部件名称
- 所属类别（如电池包、模组、外壳等）
- 拆卸工具
- 安全等级（1-5）
- 依赖关系（如果有）

返回JSON数组格式。

文档内容：
{text[:3000]}

返回格式：
[
  {{"name": "部件名", "category": "类别", "tools": ["工具1"], "safety_level": 1, "dependencies": ["依赖部件"]}}
]'''

        try:
            result = self.llm.generate(prompt)
            components = self._parse_json_array(result)
            logger.info(f"Extracted {len(components)} components")
            return components[:max_items]
        except Exception as e:
            logger.error(f"Component extraction failed: {e}")
            return []

    def extract_terms(self, text: str, max_items: int = 100) -> List[Dict[str, Any]]:
        prompt = f'''从以下技术文档中提取所有专业术语（L3层Term）。

提取要求：
- 术语名称
- 定义/解释
- 英文缩写（如果有）

返回JSON数组格式。

文档内容：
{text[:3000]}

返回格式：
[
  {{"term_id": "术语名", "definition": "定义", "units": "单位或null"}}
]'''

        try:
            result = self.llm.generate(prompt)
            terms = self._parse_json_array(result)
            logger.info(f"Extracted {len(terms)} terms")
            return terms[:max_items]
        except Exception as e:
            logger.error(f"Term extraction failed: {e}")
            return []

    def _parse_json_array(self, response: str) -> List[Dict[str, Any]]:
        response = response.strip()

        if response.startswith('['):
            try:
                return json.loads(response)
            except:
                pass

        lines = response.split('\n')
        items = []
        json_str = '['
        for line in lines:
            if '{' in line:
                json_str = line
            elif '}' in line and json_str != '[':
                json_str += '}'
                try:
                    items.append(json.loads(json_str))
                    json_str = '['
                except:
                    json_str = '['

        return items