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
        original_text = text
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
            parsed = self._parse_json_array(result)
            if parsed:
                triplets = self._normalize_triplets(parsed)
            else:
                triplets = []

            if not triplets:
                logger.warning("LLM returned no valid triplets, using deterministic text fallback")
                triplets = self._extract_triplets_fallback(original_text)
                logger.info(f"Fallback extracted {len(triplets)} raw triplets")

            if battery_model and triplets:
                for t in triplets:
                    t['battery_model'] = battery_model

            logger.info(f"Extracted {len(triplets)} triplets for {battery_model or 'unknown'}")
            return triplets[:max_items]
        except Exception as e:
            logger.error(f"Tuple extraction failed: {e}, using fallback")
            try:
                triplets = self._extract_triplets_fallback(original_text)
                logger.info(f"Fallback after exception: {len(triplets)} triplets")
                if battery_model and triplets:
                    for t in triplets:
                        t['battery_model'] = battery_model
                return triplets[:max_items]
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                return []

    def _first_scalar(self, value: Any) -> str:
        if value is None:
            return ''
        if isinstance(value, (list, tuple)):
            for item in value:
                scalar = self._first_scalar(item)
                if scalar:
                    return scalar
            return ''
        if isinstance(value, dict):
            for key in ('name', 'value', 'text', 'label', '名称'):
                scalar = self._first_scalar(value.get(key))
                if scalar:
                    return scalar
            return ''
        text = str(value).strip()
        if text in {'[]', '{}', 'null', 'None'}:
            return ''
        return text

    def _normalize_triplet(self, item: Any) -> Optional[Dict[str, Any]]:
        if isinstance(item, (list, tuple)) and len(item) >= 3:
            head, relation, tail = item[0], item[1], item[2]
            extra = {}
        elif isinstance(item, dict):
            head = next((item.get(k) for k in (
                'head', 'subject', 'source', 'from', 'start', 'head_entity',
                '头实体', '主体', '源实体', '起点', '前序部件', '前置部件'
            ) if k in item), '')
            relation = next((item.get(k) for k in (
                'relation', 'predicate', 'relationship', 'type', 'relation_type',
                '关系', '谓词', '关系类型'
            ) if k in item), '')
            tail = next((item.get(k) for k in (
                'tail', 'object', 'target', 'to', 'end', 'tail_entity',
                '尾实体', '客体', '目标实体', '终点', '后序部件', '后续部件'
) if k in item), '')
            extra = item
        else:
            return None

        normalized = {
            'head': self._first_scalar(head),
            'relation': self._first_scalar(relation),
            'tail': self._first_scalar(tail),
        }

        if len(normalized['head']) > 80 or len(normalized['tail']) > 80:
            return None
        head_lower = normalized['head'].lower()
        if re.search(r'\bi+v+\b', head_lower) and re.search(r'\bi+\b', head_lower) and len(normalized['head']) > 50:
            return None

        if not normalized['head'] or not normalized['tail']:
            return None

        if not normalized['relation']:
            normalized['relation'] = '必须先于...拆卸'

        if isinstance(extra, dict):
            for source_key, target_key in (
                ('head_tool', 'head_tool'),
                ('头实体工具', 'head_tool'),
                ('head_safety', 'head_safety'),
                ('头实体安全等级', 'head_safety'),
                ('tail_tool', 'tail_tool'),
                ('尾实体工具', 'tail_tool'),
                ('tail_safety', 'tail_safety'),
                ('尾实体安全等级', 'tail_safety'),
                ('battery_model', 'battery_model'),
            ):
                if source_key in extra:
                    normalized[target_key] = self._first_scalar(extra[source_key])

        return normalized

    def _normalize_triplets(self, items: Any) -> List[Dict[str, Any]]:
        normalized = []
        if isinstance(items, dict):
            for key in ('triplets', 'triples', 'relations', 'relationships', 'data', '三元组', '关系'):
                if isinstance(items.get(key), list):
                    items = items[key]
                    break
            else:
                items = [items]

        if not isinstance(items, list):
            return []

        seen = set()
        for item in items:
            if isinstance(item, dict):
                nested = None
                for nested_key in ('triplets', 'triples', 'relations', 'relationships', 'data', '三元组', '关系'):
                    if isinstance(item.get(nested_key), list):
                        nested = item[nested_key]
                        break
                if nested is not None:
                    for nested_item in nested:
                        triplet = self._normalize_triplet(nested_item)
                        if not triplet:
                            continue
                        key = (triplet['head'], triplet['relation'], triplet['tail'])
                        if key in seen:
                            continue
                        seen.add(key)
                        normalized.append(triplet)
                    continue

            triplet = self._normalize_triplet(item)
            if not triplet:
                continue
            key = (triplet['head'], triplet['relation'], triplet['tail'])
            if key in seen:
                continue
            seen.add(key)
            normalized.append(triplet)
        return normalized

    def _clean_component_name(self, value: str) -> str:
        value = re.sub(r'^[\d一二三四五六七八九十]+[\.、\)\s-]*', '', value.strip())
        value = re.sub(r'^(才能|可以|再|然后|继续)?(拆卸|拆除|移除|取下|断开|拔出|分离|松开)', '', value).strip()
        value = re.sub(r'(完成|后|之前|以后|然后|再)$', '', value).strip()
        value = re.sub(r'^(部件|组件|零件|名称|步骤)\s*[:：]', '', value).strip()
        value = re.sub(r'\s+', ' ', value)
        return value.strip(' ：:，,。.;；[]【】()（）')

    def _looks_like_component_line(self, line: str) -> bool:
        if not line or len(line) > 80:
            return False
        lowered = line.lower()
        blocked = {
            'head', 'tail', 'relation', 'subject', 'object', 'predicate',
            '三元组', '关系', '导入', '说明', '要求', '步骤', '工具', '安全等级'
        }
        if lowered in blocked or line in blocked:
            return False
        if re.search(r'https?://|```|\{|\}|^\|?[-:]+\|?$', line):
            return False
        return bool(re.search(r'[\w\u4e00-\u9fff]', line))

    def _append_triplet(self, triplets: List[Dict[str, Any]], head: str, relation: str, tail: str) -> None:
        head = self._clean_component_name(head)
        tail = self._clean_component_name(tail)
        relation = self._first_scalar(relation) or '必须先于...拆卸'
        if head and tail and head != tail:
            triplets.append({'head': head, 'relation': relation, 'tail': tail})

    def _extract_triplets_fallback(self, text: str, max_items: int = 100) -> List[Dict[str, Any]]:
        triplets: List[Dict[str, Any]] = []

        arrow_patterns = [
            r'(?P<head>[^,\n\r\t\-\>→]+?)\s*(?:-|=)?(?:>|→|=>|-->)\s*(?:\[?(?P<relation>[^\]→>\n\r]{1,40})\]?)\s*(?:-|=)?(?:>|→|=>|-->)\s*(?P<tail>[^\n\r]+)',
            r'(?P<head>[^,\n\r\t]+?)\s*[-=]+\s*(?P<relation>必须先于\.\.\.拆卸|必须先于.*?拆卸|需要先拆卸|拆卸顺序|precedes|before)\s*[-=]+>?\s*(?P<tail>[^\n\r]+)',
        ]
        for pattern in arrow_patterns:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                self._append_triplet(
                    triplets,
                    match.group('head'),
                    match.group('relation'),
                    match.group('tail')
                )

        for line in text.splitlines():
            stripped = line.strip().strip('|')
            if not stripped:
                continue
            parts = [p.strip().strip('|') for p in re.split(r'\s*[,，\t|]\s*', stripped) if p.strip().strip('|')]
            if len(parts) >= 3:
                first = parts[0].lower()
                if first in {'head', 'subject', '头实体', '主体'}:
                    continue
                self._append_triplet(triplets, parts[0], parts[1], parts[2])

        relation_text_patterns = [
            r'(?P<head>[\w\u4e00-\u9fff（）()\-_\s]{2,40})(?P<relation>必须先于\.\.\.拆卸|必须先于[\w\u4e00-\u9fff（）()\-_\s]*拆卸|需要先拆卸|拆卸顺序|precedes|before)(?P<tail>[\w\u4e00-\u9fff（）()\-_\s]{2,40})',
            r'(?P<head>[\w\u4e00-\u9fff（）()\-_\s]{2,40})\s+(?P<relation>precedes|before)\s+(?P<tail>[\w\u4e00-\u9fff（）()\-_\s]{2,40})',
]
        for pattern in relation_text_patterns:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                self._append_triplet(
                    triplets,
                    match.group('head'),
                    match.group('relation'),
                    match.group('tail')
                )

        explicit_patterns = [
            r'(?P<head>[\w\u4e00-\u9fff（）()\-_\s]{2,40})必须先于(?P<tail>[\w\u4e00-\u9fff（）()\-_\s]{2,40})拆卸',
            r'必须先(?:拆卸|拆除|移除|取下)?(?P<head>[\w\u4e00-\u9fff（）()\-_\s]{2,40})(?:后|，|,|才能|再)(?:拆卸|拆除|移除|取下)?(?P<tail>[\w\u4e00-\u9fff（）()\-_\s]{2,40})',
            r'先(?:拆卸|拆除|移除|取下)?(?P<head>[\w\u4e00-\u9fff（）()\-_\s]{2,40})(?:后|，|,|再)(?:拆卸|拆除|移除|取下)?(?P<tail>[\w\u4e00-\u9fff（）()\-_\s]{2,40})',
        ]
        for pattern in explicit_patterns:
            for match in re.finditer(pattern, text):
                self._append_triplet(triplets, match.group('head'), '必须先于...拆卸', match.group('tail'))

        if triplets:
            return self._normalize_triplets(triplets)[:max_items]

        ordered_components = []

        roman_numeral_pattern = r'(?:^|\.\s*)(?P<num>i{1,3}|iv|v|vi{1,3}|i{1,3}v|[ivx]+)[\.\)]\s*(?P<action>拆卸|拆除|移除|取下|断开|拔出|分离|松开|unscrew|remove|disconnect|cut|extract|separate|loosen)\s+(?P<name>[^(](?:[^()\n]{2,50}))'
        for match in re.finditer(roman_numeral_pattern, text, re.IGNORECASE):
            name = self._clean_component_name(match.group('name'))
            if name and name not in ordered_components:
                ordered_components.append(name)

        numbered_pattern = r'(?:^|\.\s*)(?P<num>\d+)[\.\)]\s*(?P<action>拆卸|拆除|移除|取下|断开|拔出|分离|松开|unscrew|remove|disconnect|cut|extract|separate|loosen)\s+(?P<name>[^(](?:[^()\n]{2,50}))'
        for match in re.finditer(numbered_pattern, text, re.IGNORECASE):
            name = self._clean_component_name(match.group('name'))
            if name and name not in ordered_components:
                ordered_components.append(name)

        ordered_components = ordered_components[:20]

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            match = re.match(
                r'^(?:步骤\s*)?[\d一二三四五六七八九十]+[\.、\)\s-]+(?:拆卸|拆除|移除|取下|断开|拔出|分离|松开)?(?P<name>[^，,。.;；\n]{2,60})',
                stripped
            )
            if match:
                name = self._clean_component_name(match.group('name'))
                if name and name not in ordered_components:
                    ordered_components.append(name)

        if not ordered_components:
            for line in text.splitlines():
                stripped = self._clean_component_name(line.strip().lstrip('-*•').strip())
                if self._looks_like_component_line(stripped) and stripped not in ordered_components:
                    ordered_components.append(stripped)

        if not ordered_components:
            inline_matches = re.findall(r'(?:拆卸|拆除|移除|取下|断开|拔出|分离|松开)([\w\u4e00-\u9fff（）()\-_]{2,30})', text)
            for name in inline_matches:
                cleaned = self._clean_component_name(name)
                if cleaned and cleaned not in ordered_components:
                    ordered_components.append(cleaned)

        for head, tail in zip(ordered_components, ordered_components[1:]):
            triplets.append({'head': head, 'relation': '必须先于...拆卸', 'tail': tail})

        return self._normalize_triplets(triplets)[:max_items]

    def extract_entities_with_types(self, text: str, filename: str = '', max_items: int = 30) -> Dict[str, Any]:
        """
        Extract entities with type classification and source evidence.
        Returns: {entities: [...], terms: [...]}
        """
        text = text[:2000]

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

重要：只返回有效的JSON对象，不要返回任何其他文字。JSON格式：
{{"entities":[{{"name":"名称","entity_type":"类型","source_evidence":"原文","battery_model":"型号"}}],"terms":[{{"term_id":"ID","name":"名称","definition":"定义"}}]}}

只返回JSON：'''

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

    def extract_terms_from_markdown(self, text: str, max_items: int = 50) -> List[Dict[str, Any]]:
        text = text[:4000]

        prompt = f'''从以下Markdown文档中提取术语定义。

文档内容：
{text}

提取要求：
1. 识别所有专业术语及其定义
2. 提取技术参数和测量单位
3. 提取安全规范相关术语

返回JSON数组格式，每个元素包含:
{{
  "term_id": "术语ID（可用序号）",
  "name": "术语名称",
  "definition": "术语定义",
  "units": "单位（如果有）"
}}

返回JSON数组：'''

        try:
            result = self.llm.generate(prompt)
            terms = self._parse_json_array(result)
            logger.info(f"Extracted {len(terms)} terms from markdown")
            return terms[:max_items]
        except Exception as e:
            logger.error(f"Term extraction from markdown failed: {e}")
            return []

    def _parse_json_object(self, response: str) -> Dict[str, Any]:
        """Parse a JSON object from LLM response."""
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
        except Exception as e:
            logger.warning(f"Failed to parse JSON object: {e}")
            try:
                import re
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    return json.loads(json_match.group(0))
            except:
                pass
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
        if filename:
            stem = filename.rsplit('.', 1)[0].strip()
            if stem:
                return re.sub(r'[^\w\u4e00-\u9fff-]+', '_', stem)
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

        try:
            parsed = json.loads(response)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                return [parsed]
        except:
            pass

        try:
            object_match = re.search(r'\{[\s\S]*\}', response)
            if object_match:
                parsed = json.loads(object_match.group(0))
                if isinstance(parsed, dict):
                    return [parsed]
        except:
            pass

        try:
            array_match = re.search(r'\[[\s\S]*\]', response)
            if array_match:
                parsed = json.loads(array_match.group(0))
                if isinstance(parsed, list):
                    return parsed
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
