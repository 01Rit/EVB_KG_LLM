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
        text = text[:2000]
        prompt = f'Extract components. Return JSON: [{{"name":"X","tools":["Y"],"safety_level":1}}]. {text}'
        try:
            result = self.llm.generate(prompt)
            components = self._parse_json_array(result)
            logger.info(f"Extracted {len(components)} components")
            return components[:max_items]
        except Exception as e:
            logger.error(f"Component extraction failed: {e}")
            return []

    def extract_terms(self, text: str, max_items: int = 100) -> List[Dict[str, Any]]:
        text = text[:2000]
        prompt = f'Extract terms. Return JSON: [{{"term_id":"X","definition":"Y"}}]. {text}'
        try:
            result = self.llm.generate(prompt)
            terms = self._parse_json_array(result)
            logger.info(f"Extracted {len(terms)} terms")
            return terms[:max_items]
        except Exception as e:
            logger.error(f"Term extraction failed: {e}")
            return []

    def extract_triplets(self, text: str, max_items: int = 100, filename: str = '') -> List[Dict[str, Any]]:
        text = text[:3000]

        battery_model = self._detect_battery_model(text, filename)
        logger.info(f"Detected battery model: {battery_model}")

        prompt = f'''从以下电池拆卸手册中提取知识图谱三元组，构建完整的拆卸序列图。

【重要】拆卸序列的关键是提取"必须在X之前拆卸Y"的关系，这决定了拓扑排序的依赖图。

文档内容：
{text}

提取要求：
1. 识别所有可拆卸部件
2. 提取部件间的拆卸依赖关系（如：必须先拆A才能拆B）
3. 提取工具、安全等级等信息作为节点属性

返回JSON数组格式，每个元素包含:
{{
  "head": "部件名称",        # 头实体
  "tail": "部件名称",        # 尾实体（被依赖的部件）
  "relation": "拆卸顺序",   # 关系类型
  "head_tool": "工具1,工具2",  # 头部件所需工具
  "head_safety": 1,        # 头部件安全等级 1-5
  "tail_tool": "工具1",    # 尾部件所需工具
  "tail_safety": 2         # 尾部件安全等级 1-5
}}

关系类型定义：
- "是...的子部件"：整体与部分（如 电池包-模组）
- "必须先于...拆卸"：拆卸顺序依赖（如 盖板必须先于模组拆卸）
- "需要工具"：工具关联
- "需要先拆卸"：拆卸前置条件

【重要】每个三元组必须形成完整的拆卸链，确保图是连通的。如果文档中只有"拆卸盖板、拆卸绝缘层、拆卸模组"，则生成：
[
  {{"head":"电池盖板","tail":"绝缘层","relation":"必须先于...拆卸"}},
  {{"head":"绝缘层","tail":"模组","relation":"必须先于...拆卸"}},
  {{"head":"电池盖板","tail":"模组","relation":"是...的子部件"}}
]

返回JSON数组：'''

        try:
            result = self.llm.generate(prompt)
            triplets = self._parse_json_array(result)

            if battery_model and triplets:
                for t in triplets:
                    t['battery_model'] = battery_model

            logger.info(f"Extracted {len(triplets)} triplets for {battery_model or 'unknown'}")
            return triplets[:max_items]
        except Exception as e:
            logger.error(f"Triplet extraction failed: {e}")
            return []

    def extract_entities_with_types(self, text: str, filename: str = '', max_items: int = 100) -> Dict[str, Any]:
        """
        Extract entities with type classification and source evidence.
        Returns: {entities: [...], terms: [...]}
        """
        text = text[:4000]

        battery_model = self._detect_battery_model(text, filename)
        logger.info(f"Detected battery model: {battery_model}")

        prompt = f'''从以下电池拆卸手册中提取实体知识，构建三层知识图谱。

文档内容：
{text}

提取要求：
1. 识别所有可拆卸部件（component）：电池包、模组、电芯、冷却板等
2. 识别工具（tool）：扭矩扳手、绝缘工具、拆卸夹具等
3. 识别动作（action）：拆卸、拧松、拔出、分离、检测等
4. 识别技术参数（parameter）：扭矩值25Nm、电压阈值、绝缘电阻等
5. 识别安全规范（safety）：高压安全距离、IP67防护等级、防触电措施等
6. 识别材料/属性（material）：阻燃材料、铝合金外壳、冷却液类型等
7. 识别定义（definition）：预紧力、力矩标准、拆卸顺序规则等

返回JSON：
{{
  "entities": [
    {{
      "name": "实体名称",
      "entity_type": "component|tool|action|parameter|safety|material|definition",
      "source_evidence": "原文摘录",
      "battery_model": "{battery_model or 'unknown'}"
    }}
  ],
  "terms": [
    {{
      "term_id": "术语ID",
      "name": "术语名称",
      "definition": "术语定义"
    }}
  ]
}}

只返回JSON数组：'''

        try:
            result = self.llm.generate(prompt)
            data = self._parse_json_object(result)
            entities = data.get('entities', [])
            terms = data.get('terms', [])
            logger.info(f"Extracted {len(entities)} entities, {len(terms)} terms for {battery_model or 'unknown'}")
            return {'entities': entities[:max_items], 'terms': terms[:max_items]}
        except Exception as e:
            logger.error(f"Entity type extraction failed: {e}")
            return {'entities': [], 'terms': []}

    def _parse_json_object(self, response: str) -> Dict[str, Any]:
        """Parse a JSON object from LLM response."""
        import json
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            json_content = []
            in_code_block = False
            for line in lines:
                if line.startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if in_code_block:
                    json_content.append(line)
            response = "\n".join(json_content)
        try:
            return json.loads(response)
        except:
            return {}

    def _detect_battery_model(self, text: str, filename: str = '') -> Optional[str]:
        combined = text + ' ' + filename
        patterns = [
            r'Audi[_\s]?A3',
            r'EVB',
            r'Battery\s*Model[:\s]*(\w+)',
            r'车型[:\s]*(\w+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, combined, re.IGNORECASE)
            if match:
                if 'Audi' in match.group(0):
                    return 'Audi_A3'
                return match.group(1) if match.groups() else match.group(0)
        return None

    def _parse_json_array(self, response: str) -> List[Dict[str, Any]]:
        response = response.strip()

        if response.startswith("```"):
            lines = response.split("\n")
            json_content = []
            in_code_block = False
            for line in lines:
                if line.startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if in_code_block:
                    json_content.append(line)
            response = "\n".join(json_content)

        if response.startswith("["):
            try:
                return json.loads(response)
            except:
                pass

        lines = response.split("\n")
        items = []
        json_str = "["
        for line in lines:
            if "{" in line:
                json_str = line
            elif "}" in line and json_str != "[":
                json_str += "}"
                try:
                    items.append(json.loads(json_str))
                    json_str = "["
                except:
                    json_str = "["

        return items
