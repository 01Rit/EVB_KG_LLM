# 三层知识图谱跨层连接实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现四步跨层连接管道，在L1/L2/L3层之间建立 REFERENCE_OF 和 DEFINITION_OF 关系，同时保持拆卸序列规划模块完全不受影响。

**Architecture:**
- 新建 `src/cross_layer/` 模块，实现四步管道：Embedding召回 → 硬规则过滤 → LLM精判 → 图写入
- 跨层检索作为独立模块透明插入现有GraphRAG流程，按需触发
- 拆卸序列模块（`sequence/`）零改动

**Tech Stack:** Neo4j, Milvus, OpenAI LLM, Pydantic

---

## Module Structure

```
src/cross_layer/
├── __init__.py              # 模块导出
├── linker.py                # 四步管道主逻辑
├── embedder.py              # Embedding生成 + Milvus检索
├── rules.py                 # 硬规则过滤：层间类型映射表
├── llm_judge.py             # LLM精判
├── write_policy.py          # 写入策略：阈值 + Top-K
└── merger.py                # 跨层结果与现有证据合并

src/graphrag/
└── cross_layer_retriever.py # 透明插入：跨层检索集成（新增文件）
```

---

## Task 1: 创建 cross_layer 模块骨架

**Files:**
- Create: `src/cross_layer/__init__.py`
- Create: `src/cross_layer/rules.py`
- Create: `src/cross_layer/embedder.py`
- Create: `src/cross_layer/llm_judge.py`
- Create: `src/cross_layer/write_policy.py`
- Create: `src/cross_layer/linker.py`
- Create: `src/cross_layer/merger.py`

- [ ] **Step 1: 创建目录和 __init__.py**

```python
# src/cross_layer/__init__.py
from src.cross_layer.linker import CrossLayerLinker
from src.cross_layer.rules import CrossLayerRules
from src.cross_layer.embedder import CrossLayerEmbedder
from src.cross_layer.llm_judge import LLMJudge
from src.cross_layer.write_policy import WritePolicy
from src.cross_layer.merger import CrossLayerMerger

__all__ = [
    'CrossLayerLinker',
    'CrossLayerRules',
    'CrossLayerEmbedder',
    'LLMJudge',
    'WritePolicy',
    'CrossLayerMerger',
]
```

- [ ] **Step 2: 创建 rules.py - 层间类型映射表**

```python
# src/cross_layer/rules.py
from dataclasses import dataclass
from typing import Set, Dict

RELATION_TYPE_MAPPING = {
    'REFERENCE_OF': {
        'allowed_pairs': {
            ('Component', 'Component'),
            ('Component', 'Document'),
            ('Component', 'Term'),
            ('Document', 'Entity'),
            ('Document', 'Term'),
        },
        'source_layer': 'L1',
        'target_layer': 'L2',
    },
    'DEFINITION_OF': {
        'allowed_pairs': {
            ('Entity', 'Term'),
            ('Term', 'Entity'),
        },
        'source_layer': 'L2',
        'target_layer': 'L3',
    },
    'CONSTRAINED_BY': {
        'allowed_pairs': {
            ('Component', 'Term'),
        },
        'source_layer': 'L1',
        'target_layer': 'L3',
    },
}

CONFIDENCE_THRESHOLDS = {
    'REFERENCE_OF': {'high': 0.92, 'low': 0.80},
    'DEFINITION_OF': {'high': 0.90, 'low': 0.75},
    'CONSTRAINED_BY': {'high': 0.88, 'low': 0.70},
}


@dataclass
class CrossLayerRules:
    @staticmethod
    def is_valid_relation_type(source_type: str, target_type: str, relation_type: str) -> bool:
        pair = (source_type, target_type)
        mapping = RELATION_TYPE_MAPPING.get(relation_type)
        if not mapping:
            return False
        return pair in mapping['allowed_pairs']

    @staticmethod
    def is_valid_direction(source_layer: str, target_layer: str, relation_type: str) -> bool:
        mapping = RELATION_TYPE_MAPPING.get(relation_type)
        if not mapping:
            return False
        return source_layer == mapping['source_layer'] and target_layer == mapping['target_layer']

    @staticmethod
    def get_confidence_band(score: float, relation_type: str) -> str:
        thresholds = CONFIDENCE_THRESHOLDS.get(relation_type, {'high': 0.90, 'low': 0.75})
        if score >= thresholds['high']:
            return 'high'
        elif score >= thresholds['low']:
            return 'medium'
        else:
            return 'low'
```

- [ ] **Step 3: 创建 embedder.py - Embedding生成与Milvus检索**

```python
# src/cross_layer/embedder.py
import openai
from src.kg.client import MilvusClient
from typing import List, Dict, Optional


class CrossLayerEmbedder:
    def __init__(self, milvus_client: Optional[MilvusClient] = None):
        self.milvus = milvus_client

    def compute_embedding(self, text: str) -> List[float]:
        response = openai.embeddings.create(
            model='text-embedding-3-small',
            input=text
        )
        return response.data[0].embedding

    def build_entity_text(self, name: str, entity_type: str, context: str = '') -> str:
        return f"{entity_type}: {name}. {context}".strip()

    def recall_candidates(
        self,
        entity_name: str,
        entity_type: str,
        target_layer: str,
        target_relation: str,
        top_k: int = 30
    ) -> List[Dict]:
        if not self.milvus:
            return []
        entity_text = self.build_entity_text(entity_name, entity_type)
        query_vector = self.compute_embedding(entity_text)
        milvus_results = self.milvus.search(query_vector, top_k=top_k)
        candidates = []
        for hit in milvus_results:
            hit_layer = hit.get('layer', '')
            hit_type = hit.get('type', '')
            if hit_layer == target_layer:
                candidates.append({
                    'source_name': entity_name,
                    'source_type': entity_type,
                    'target_name': hit.get('name', ''),
                    'target_type': hit_type,
                    'target_id': hit.get('id', ''),
                    'score': 1 - hit.get('distance', 0),
                    'layer': hit_layer,
                })
        return candidates
```

- [ ] **Step 4: 创建 llm_judge.py - LLM精判**

```python
# src/cross_layer/llm_judge.py
from src.utils.llm_client import LLMClient
from src.cross_layer.rules import CrossLayerRules
from typing import Dict, Optional


RELATION_PROMPT_TEMPLATE = """你是一个跨层关系判断专家。判断以下两个实体之间是否应该建立 {relation_type} 关系。

源实体：
- 名称：{source_name}
- 类型：{source_type}
- 上下文：{source_context}

目标实体：
- 名称：{target_name}
- 类型：{target_type}
- 上下文：{target_context}

业务约束：
- 该关系必须符合层间类型映射规则
- REFERENCE_OF：L1拆卸组件 → L2知识实体，表示拆卸操作有标准依据
- DEFINITION_OF：L2知识实体 → L3术语定义，表示概念有明确定义

请判断：是否应该建立 {relation_type} 关系？
输出格式：
{{"decision": "YES"或"NO", "confidence": 0.0~1.0, "reason": "判断理由"}}
"""


class LLMJudge:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def judge(
        self,
        source_name: str,
        source_type: str,
        source_context: str,
        target_name: str,
        target_type: str,
        target_context: str,
        relation_type: str,
    ) -> Dict:
        prompt = RELATION_PROMPT_TEMPLATE.format(
            relation_type=relation_type,
            source_name=source_name,
            source_type=source_type,
            source_context=source_context or '无',
            target_name=target_name,
            target_type=target_type,
            target_context=target_context or '无',
        )
        response = self.llm.chat([{'role': 'user', 'content': prompt}])
        try:
            import json
            result = json.loads(response)
            return result
        except Exception:
            return {'decision': 'NO', 'confidence': 0.0, 'reason': '解析失败'}
```

- [ ] **Step 5: 创建 write_policy.py - 写入策略**

```python
# src/cross_layer/write_policy.py
from typing import Dict, List
from collections import defaultdict


class WritePolicy:
    def __init__(self, top_k_per_relation: int = 3):
        self.top_k = top_k_per_relation

    def filter_by_threshold(
        self,
        candidates: List[Dict],
        relation_type: str,
        thresholds: Dict
    ) -> List[Dict]:
        threshold = thresholds.get(relation_type, {'low': 0.75})
        return [
            c for c in candidates
            if c.get('final_score', 0) >= threshold['low']
        ]

    def apply_top_k(
        self,
        candidates: List[Dict],
        relation_type: str
    ) -> List[Dict]:
        grouped = defaultdict(list)
        for c in candidates:
            key = (c.get('source_id'), relation_type)
            grouped[key].append(c)
        result = []
        for key, items in grouped.items():
            sorted_items = sorted(items, key=lambda x: x.get('final_score', 0), reverse=True)
            result.extend(sorted_items[:self.top_k])
        return result
```

- [ ] **Step 6: 创建 linker.py - 四步管道主逻辑**

```python
# src/cross_layer/linker.py
from typing import List, Dict, Optional
from src.kg.client import Neo4jClient, MilvusClient
from src.utils.llm_client import LLMClient
from src.cross_layer.embedder import CrossLayerEmbedder
from src.cross_layer.rules import CrossLayerRules, CONFIDENCE_THRESHOLDS
from src.cross_layer.llm_judge import LLMJudge
from src.cross_layer.write_policy import WritePolicy


class CrossLayerLinker:
    def __init__(
        self,
        neo4j_client: Neo4jClient,
        milvus_client: Optional[MilvusClient] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        self.neo4j = neo4j_client
        self.embedder = CrossLayerEmbedder(milvus_client)
        self.rules = CrossLayerRules()
        self.llm_judge = LLMJudge(llm_client) if llm_client else None
        self.write_policy = WritePolicy(top_k_per_relation=3)

    def run_pipeline(
        self,
        source_node_id: str,
        source_name: str,
        source_type: str,
        source_layer: str,
        source_context: str,
        target_layer: str,
        relation_type: str,
    ) -> List[Dict]:
        candidates = self._step1_embed_recall(
            source_name, source_type, source_context, target_layer, relation_type
        )
        if not candidates:
            return []

        filtered = self._step2_hard_rule_filter(candidates, source_type, relation_type)
        if not filtered:
            return []

        judged = self._step3_llm_judge(filtered, source_context, relation_type)
        final = self._step4_write_policy(judged, relation_type)
        return final

    def _step1_embed_recall(
        self,
        source_name: str,
        source_type: str,
        source_context: str,
        target_layer: str,
        relation_type: str,
    ) -> List[Dict]:
        return self.embedder.recall_candidates(
            entity_name=source_name,
            entity_type=source_type,
            target_layer=target_layer,
            target_relation=relation_type,
            top_k=30,
        )

    def _step2_hard_rule_filter(
        self,
        candidates: List[Dict],
        source_type: str,
        relation_type: str,
    ) -> List[Dict]:
        filtered = []
        for c in candidates:
            if not self.rules.is_valid_relation_type(source_type, c['target_type'], relation_type):
                continue
            if not self.rules.is_valid_direction('L1', c['layer'], relation_type):
                continue
            filtered.append(c)
        return filtered

    def _step3_llm_judge(
        self,
        candidates: List[Dict],
        source_context: str,
        relation_type: str,
    ) -> List[Dict]:
        if not self.llm_judge:
            return candidates
        judged = []
        for c in candidates:
            band = self.rules.get_confidence_band(c['score'], relation_type)
            if band == 'high':
                c['final_score'] = c['score']
                c['decision'] = 'YES'
                judged.append(c)
            elif band == 'medium':
                result = self.llm_judge.judge(
                    source_name=c['source_name'],
                    source_type=c['source_type'],
                    source_context=source_context,
                    target_name=c['target_name'],
                    target_type=c['target_type'],
                    target_context='',
                    relation_type=relation_type,
                )
                c['final_score'] = result.get('confidence', 0.0)
                c['decision'] = result.get('decision', 'NO')
                if c['decision'] == 'YES':
                    judged.append(c)
            # low band: skip
        return judged

    def _step4_write_policy(
        self,
        candidates: List[Dict],
        relation_type: str,
    ) -> List[Dict]:
        threshold_filtered = self.write_policy.filter_by_threshold(
            candidates, relation_type, CONFIDENCE_THRESHOLDS
        )
        return self.write_policy.apply_top_k(threshold_filtered, relation_type)

    def write_relations(self, relations: List[Dict], relation_type: str) -> int:
        if not relations:
            return 0
        cypher = f"""
        MATCH (s), (t)
        WHERE s.id = $source_id AND t.id = $target_id
        MERGE (s)-[r:{relation_type}]->(t)
        RETURN count(r) as cnt
        """
        count = 0
        for rel in relations:
            result = self.neo4j.execute_query(cypher, {
                'source_id': rel['source_id'],
                'target_id': rel['target_id'],
            })
            count += result[0].get('cnt', 0) if result else 0
        return count
```

- [ ] **Step 7: 创建 merger.py - 跨层结果与现有证据合并**

```python
# src/cross_layer/merger.py
from src.kg.models import EvidenceNode, EvidenceGraph
from typing import List


class CrossLayerMerger:
    @staticmethod
    def merge(
        original_graph: EvidenceGraph,
        cross_layer_nodes: List[EvidenceNode],
        cross_layer_edges: List[dict],
        max_nodes: int = 100,
    ) -> EvidenceGraph:
        existing_ids = {n.id for n in original_graph.nodes}
        for node in cross_layer_nodes:
            if node.id not in existing_ids:
                original_graph.nodes.append(node)
                existing_ids.add(node.id)
        for edge in cross_layer_edges:
            original_graph.edges.append(edge)
        original_graph.nodes = original_graph.nodes[:max_nodes]
        return original_graph
```

- [ ] **Step 8: Commit**

```bash
git add src/cross_layer/
git commit -m "feat: add cross_layer module skeleton"
```

---

## Task 2: 创建 GraphRAG 透明插入模块

**Files:**
- Create: `src/graphrag/cross_layer_retriever.py`
- Modify: `src/graphrag/planner.py` (集成点)

- [ ] **Step 1: 创建 cross_layer_retriever.py**

```python
# src/graphrag/cross_layer_retriever.py
from typing import Optional
from src.cross_layer.linker import CrossLayerLinker
from src.kg.client import Neo4jClient, MilvusClient
from src.utils.llm_client import LLMClient
from src.kg.models import EvidenceGraph
import logging

logger = logging.getLogger(__name__)


class CrossLayerRetriever:
    def __init__(
        self,
        neo4j_client: Neo4jClient,
        milvus_client: Optional[MilvusClient] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        self.linker = CrossLayerLinker(neo4j_client, milvus_client, llm_client)

    def should_trigger(self, graph: EvidenceGraph) -> bool:
        if len(graph.nodes) < 5:
            return True
        return False

    def retrieve_cross_layer(
        self,
        battery_model: str,
        intents: list[str],
    ) -> EvidenceGraph:
        relations_written = 0
        for intent in intents:
            l1_components = self.linker.neo4j.search_components(intent, top_k=10)
            for comp in l1_components:
                refs = self.linker.run_pipeline(
                    source_node_id=comp.get('id', ''),
                    source_name=comp.get('name', ''),
                    source_type='Component',
                    source_layer='L1',
                    source_context=comp.get('battery_model', ''),
                    target_layer='L2',
                    relation_type='REFERENCE_OF',
                )
                relations_written += self.linker.write_relations(refs, 'REFERENCE_OF')
        logger.info(f"Cross-layer relations written: {relations_written}")
        return EvidenceGraph(nodes=[], edges=[])
```

- [ ] **Step 2: 修改 planner.py 集成点**

在 `Planner.__init__` 中添加 cross_layer_retriever 初始化（不修改现有retriever逻辑）：

```python
# src/graphrag/planner.py 第26-32行附近
# 在 use_constraint_retriever 分支后添加：

if neo4j_client:
    from src.graphrag.cross_layer_retriever import CrossLayerRetriever
    self.cross_layer_retriever = CrossLayerRetriever(neo4j_client, milvus_client, llm_client)
else:
    self.cross_layer_retriever = None
```

- [ ] **Step 3: Commit**

```bash
git add src/graphrag/cross_layer_retriever.py src/graphrag/planner.py
git commit -m "feat: add CrossLayerRetriever integration point"
```

---

## Task 3: 添加触发条件判断

**Files:**
- Modify: `src/graphrag/cross_layer_retriever.py`

- [ ] **Step 1: 实现三重条件触发**

```python
# 在 CrossLayerRetriever.should_trigger 中实现：
# 1. Coverage：关键概念覆盖率
# 2. Structure completeness：证据子图结构完整性
# 3. Minimum evidence：证据数量最小值
```

- [ ] **Step 2: Commit**

```bash
git add src/graphrag/cross_layer_retriever.py
git commit -m "feat: add trigger conditions for cross-layer retrieval"
```

---

## Task 4: 验证与测试

**Files:**
- Create: `tests/cross_layer/test_rules.py`
- Create: `tests/cross_layer/test_linker.py`
- Create: `tests/cross_layer/test_integration.py`

- [ ] **Step 1: 编写 rules 测试**

```python
# tests/cross_layer/test_rules.py
import pytest
from src.cross_layer.rules import CrossLayerRules, CONFIDENCE_THRESHOLDS

def test_is_valid_relation_type_reference_of():
    assert CrossLayerRules.is_valid_relation_type('Component', 'Document', 'REFERENCE_OF') is True
    assert CrossLayerRules.is_valid_relation_type('Component', 'Term', 'REFERENCE_OF') is True
    assert CrossLayerRules.is_valid_relation_type('Component', 'Component', 'REFERENCE_OF') is True

def test_is_valid_relation_type_definition_of():
    assert CrossLayerRules.is_valid_relation_type('Entity', 'Term', 'DEFINITION_OF') is True
    assert CrossLayerRules.is_valid_relation_type('Term', 'Entity', 'DEFINITION_OF') is False

def test_confidence_band():
    assert CrossLayerRules.get_confidence_band(0.95, 'REFERENCE_OF') == 'high'
    assert CrossLayerRules.get_confidence_band(0.85, 'REFERENCE_OF') == 'medium'
    assert CrossLayerRules.get_confidence_band(0.70, 'REFERENCE_OF') == 'low'
```

- [ ] **Step 2: 运行测试验证**

```bash
python -m pytest tests/cross_layer/test_rules.py -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/cross_layer/
git commit -m "test: add cross_layer unit tests"
```

---

## Task 5: API 路由（可选，按需）

**Files:**
- Create: `src/api/cross_layer_routes.py`（如需手动触发跨层建边）
- Modify: `src/main.py`（注册路由）

---

## 验证命令

```bash
# 验证跨层关系数量分布
python -c "
from src.kg.client import Neo4jClient
from src.config import settings
client = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
result = client.execute_query('''
MATCH (s)-[r]->(t)
WHERE type(r) IN [\"REFERENCE_OF\", \"DEFINED_OF\", \"CONSTRAINED_BY\"]
RETURN type(r) as relation_type, count(*) as count
''')
print(result)
"

# 运行测试
python -m pytest tests/cross_layer/ -v
```

---

## Spec Coverage Check

| 设计要求 | 对应任务 |
|----------|----------|
| 四步管道 | Task 1 (linker.py) |
| 层间类型映射表 + Hard Constraint | Task 1 (rules.py) |
| 置信度分关系类型阈值 | Task 1 (rules.py CONFIDENCE_THRESHOLDS) |
| LLM精判 Prompt | Task 1 (llm_judge.py) |
| Top-K per source_node + relation_type | Task 1 (write_policy.py) |
| 透明插入 GraphRAG | Task 2 |
| 按需触发（Coverage + Structure + MinEvidence） | Task 3 |
| 结果合并 | Task 1 (merger.py) |
| 拆卸序列模块零改动 | 验证：sequence/ 未被修改 |
