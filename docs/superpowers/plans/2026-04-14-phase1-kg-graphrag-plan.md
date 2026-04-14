# 阶段1：核心知识图谱 + GraphRAG推理模块 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建基于知识图谱的智能拆卸规划推理系统，支持自然语言查询返回结构化拆卸方案

**Architecture:** 使用增强型GraphRAG（Query Rewriting + Multi-Path检索 + 证据排序 + 迭代补充），Neo4j存储图数据 + Milvus向量检索 + GPT-4o生成

**Tech Stack:** Python 3.11+, FastAPI, Neo4j 5.20+, Milvus 2.4+, OpenAI GPT-4o

---

## 文件结构

```
src/
├── __init__.py
├── main.py
├── config.py
├── logs.py
├── kg/
│   ├── __init__.py
│   ├── client.py
│   ├── models.py
│   ├── indexes.py
│   └── importer.py
├── graphrag/
│   ├── __init__.py
│   ├── query_rewriter.py
│   ├── retriever.py
│   ├── ranker.py
│   ├── generator.py
│   ├── feedback.py
│   └── planner.py
├── api/
│   ├── __init__.py
│   ├── routes.py
│   ├── schemas.py
│   └── middleware.py
└── utils/
    ├── __init__.py
    └── llm_client.py

tests/
├── kg/
│   └── test_client.py
├── graphrag/
│   └── test_planner.py
└── api/
    └── test_routes.py

.env.example
requirements.txt
docker-compose.yml
```

---

### Task 1: 项目基础设置

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `src/__init__.py`
- Create: `src/config.py`
- Create: `src/logs.py`

- [ ] **Step 1: 创建 requirements.txt**

```txt
fastapi==0.109.0
uvicorn==0.27.0
neo4j==5.18.0
pymilvus==2.4.0
openai==1.12.0
pydantic==2.5.3
pydantic-settings==2.1.0
python-dotenv==1.0.0
pytest==8.0.0
pytest-asyncio==0.23.0
httpx==0.26.0
```

- [ ] **Step 2: 创建 .env.example**

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here
MILVUS_HOST=localhost
MILVUS_PORT=19530
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
LOG_LEVEL=INFO
```

- [ ] **Step 3: 创建 src/__init__.py**

```python
```

- [ ] **Step 4: 创建 src/config.py**

```python
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    neo4j_uri: str = bolt://localhost:7687
    neo4j_user: str = neo4j
    neo4j_password: str
    milvus_host: str = localhost
    milvus_port: int = 19530
    openai_api_key: str
    openai_base_url: str = https://api.openai.com/v1
    log_level: str = INFO
    
    model: str = gpt-4o
    temperature: float = 0.1
    max_tokens: int = 2000
    
    top_k: int = 30
    retrieval_depth: int = 2
    similarity_threshold: float = 0.72
    max_iterations: int = 3
    
    class Config:
        env_file = .env
        extra = ignore


settings = Settings()
```

- [ ] **Step 5: 创建 src/logs.py**

```python
import logging
import sys
from src.config import settings


def setup_logging():
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


logger = setup_logging()
```

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .env.example src/__init__.py src/config.py src/logs.py
git commit -m feat: add project baseline (requirements, config, logging)
```

---

### Task 2: 知识图谱客户端

**Files:**
- Create: `src/kg/__init__.py`
- Create: `src/kg/models.py`
- Create: `src/kg/client.py`
- Create: `tests/kg/test_client.py`

- [ ] **Step 1: 创建 src/kg/__init__.py**

```python
```

- [ ] **Step 2: 创建 src/kg/models.py**

```python
from pydantic import BaseModel
from typing import Optional, Any


class Component(BaseModel):
    id: str
    name: str
    battery_model: str
    tool_required: list[str] = []
    safety_level: int = 1
    preconditions: list[str] = []
    estimated_time: int = 0
    metadata: dict[str, Any] = {}


class Document(BaseModel):
    doc_id: str
    title: str
    source: str
    source_type: str
    content: str
    metadata: dict[str, Any] = {}


class Term(BaseModel):
    term_id: str
    definition: str
    units: Optional[str] = None
    related_components: list[str] = []


class EvidenceNode(BaseModel):
    node_type: str
    id: str
    name: str
    properties: dict[str, Any]
    relationships: list[str] = []
    text: str


class EvidenceGraph(BaseModel):
    nodes: list[EvidenceNode] = []
    edges: list[dict] = []
    
    def expand(self, new_nodes: list[EvidenceNode]):
        existing_ids = {n.id for n in self.nodes}
        for node in new_nodes:
            if node.id not in existing_ids:
                self.nodes.append(node)
    
    def to_text(self) -> str:
        texts = []
        for node in self.nodes:
            texts.append(f[{node.node_type}: {node.name}] - {node.text})
        return '\n\n'.join(texts)
```

- [ ] **Step 3: 创建 src/kg/client.py**

```python
from neo4j import GraphDatabase
from pymilvus import connections, Collection
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)


class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def verify_connectivity(self) -> bool:
        try:
            self.driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error(fNeo4j connectivity check failed: {e})
            return False
    
    def execute_query(self, query: str, parameters: dict = None):
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    
    def search_components(self, query: str, top_k: int = 30) -> list[dict]:
        cypher = '''
        MATCH (c:Component)
        WHERE c.name CONTAINS $query OR c.battery_model CONTAINS $query
        RETURN c.id as id, c.name as name, c.battery_model as battery_model,
               c.tool_required as tool_required, c.safety_level as safety_level
        LIMIT $top_k
        '''
        return self.execute_query(cypher, {'query': query, 'top_k': top_k})
    
    def search_documents(self, query: str, top_k: int = 30) -> list[dict]:
        cypher = '''
        MATCH (d:Document)
        WHERE d.title CONTAINS $query OR d.content CONTAINS $query
        RETURN d.doc_id as doc_id, d.title as title, d.source as source,
               d.source_type as source_type, d.content as content
        LIMIT $top_k
        '''
        return self.execute_query(cypher, {'query': query, 'top_k': top_k})
    
    def search_terms(self, query: str, top_k: int = 30) -> list[dict]:
        cypher = '''
        MATCH (t:Term)
        WHERE t.term_id CONTAINS $query OR t.definition CONTAINS $query
        RETURN t.term_id as term_id, t.definition as definition, t.units as units
        LIMIT $top_k
        '''
        return self.execute_query(cypher, {'query': query, 'top_k': top_k})
    
    def get_subgraph(self, node_ids: list[str], depth: int = 2) -> dict:
        if not node_ids:
            return {'nodes': [], 'edges': []}
        
        cypher = '''
        MATCH path = (c:Component)-[r*1..{depth}]-(related)
        WHERE c.id IN $node_ids
        RETURN nodes(path) as nodes, relationships(path) as rels
        '''.format(depth=depth)
        
        results = self.execute_query(cypher, {'node_ids': node_ids})
        
        nodes = []
        edges = []
        seen_nodes = set()
        seen_rels = set()
        
        for record in results:
            for node in record.get('nodes', []):
                if node.element_id not in seen_nodes:
                    seen_nodes.add(node.element_id)
                    nodes.append({
                        'id': node.get('id'),
                        'labels': list(node.labels),
                        'properties': dict(node)
                    })
            
            for rel in record.get('rels', []):
                rel_key = f{rel.start_node.element_id}-{rel.element_id}
                if rel_key not in seen_rels:
                    seen_rels.add(rel_key)
                    edges.append({
                        'start': rel.start_node.get('id'),
                        'end': rel.end_node.get('id'),
                        'type': rel.type,
                        'properties': dict(rel)
                    })
        
        return {'nodes': nodes, 'edges': edges}
    
    def get_battery_model_components(self, battery_model: str) -> list[dict]:
        cypher = '''
        MATCH (c:Component {battery_model: $model})
        RETURN c.id as id, c.name as name, c.tool_required as tool_required,
               c.safety_level as safety_level
        ORDER BY c.name
        '''
        return self.execute_query(cypher, {'model': battery_model})


class MilvusClient:
    def __init__(self, host: str, port: int):
        connections.connect(alias=default, host=host, port=port)
        self.collection: Optional[Collection] = None
    
    def close(self):
        connections.disconnect(alias=default)
    
    def set_collection(self, name: str):
        self.collection = Collection(name)
        self.collection.load()
    
    def search(self, query_vector: list[float], top_k: int = 30) -> list[dict]:
        if not self.collection:
            raise RuntimeError(Collection not initialized)
        
        search_params = {'metric_type': 'COSINE', 'params': {}}
        results = self.collection.search(
            data=[query_vector],
            anns_field='embedding',
            param=search_params,
            limit=top_k,
            output_fields=['id', 'text', 'type']
        )
        
        return [
            {'id': hit.entity.get('id'), 'text': hit.entity.get('text'), 
             'type': hit.entity.get('type'), 'distance': hit.distance}
            for hit in results[0]
        ]
```

- [ ] **Step 4: 创建 tests/kg/test_client.py**

```python
import pytest
from src.kg.client import Neo4jClient, MilvusClient


def test_neo4j_client_import():
    assert Neo4jClient is not None


def test_milvus_client_import():
    assert MilvusClient is not None
```

- [ ] **Step 5: 运行测试验证失败**

```bash
cd D:/KG_project/Final4.14
python -m pytest tests/kg/test_client.py -v
```

- [ ] **Step 6: Commit**

```bash
git add src/kg/ tests/kg/ 
git commit -m feat: add KG client (Neo4j + Milvus)
```

---

### Task 3: LLM客户端封装

**Files:**
- Create: `src/utils/__init__.py`
- Create: `src/utils/llm_client.py`

- [ ] **Step 1: 创建 src/utils/__init__.py**

```python
```

- [ ] **Step 2: 创建 src/utils/llm_client.py**

```python
from openai import OpenAI
from typing import Optional
import logging
import json

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, api_key: str, base_url: str = https://api.openai.com/v1, 
                 model: str = gpt-4o, temperature: float = 0.1, max_tokens: int = 2000):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    def generate(self, prompt: str, system_message: Optional[str] = None,
                 response_format: Optional[dict] = None) -> str:
        messages = []
        if system_message:
            messages.append({'role': 'system', 'content': system_message})
        messages.append({'role': 'user', 'content': prompt})
        
        kwargs = {
            'model': self.model,
            'messages': messages,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        }
        if response_format:
            kwargs['response_format'] = response_format
        
        try:
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            logger.error(fLLM generation failed: {e})
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
```

- [ ] **Step 3: Commit**

```bash
git add src/utils/llm_client.py
git commit -m feat: add LLM client wrapper
```

---

### Task 4: GraphRAG - Query Rewriter

**Files:**
- Create: `src/graphrag/__init__.py`
- Create: `src/graphrag/query_rewriter.py`
- Create: `tests/graphrag/test_query_rewriter.py`

- [ ] **Step 1: 创建 src/graphrag/__init__.py**

```python
```

- [ ] **Step 2: 创建 src/graphrag/query_rewriter.py**

```python
from src.utils.llm_client import LLMClient
from typing import list
import logging
import json
import re

logger = logging.getLogger(__name__)


class QueryRewriter:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
    
    def rewrite(self, original_query: str, context: list[str] = None) -> list[str]:
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
            logger.info(fRewrote query into {len(intents)} intents)
            return intents
        except Exception as e:
            logger.warning(fQuery rewriting failed, using original: {e})
            return [original_query]
    
    def _parse_intents(self, response: str) -> list[str]:
        response = response.strip()
        
        if response.startswith('['):
            try:
                intents = json.loads(response)
                if isinstance(intents, list):
                    return [str(i) for i in intents]
            except:
                pass
        
        lines = response.split('\n')
        intents = []
        for line in lines:
            line = line.strip()
            line = re.sub(r'^[\"-]\\s*', '', line)
            line = re.sub(r'^\\d+\\.\\s*', '', line)
            if line and len(line) > 3:
                intents.append(line)
        
        return intents[:5] if intents else [response]
```

- [ ] **Step 3: 创建 tests/graphrag/test_query_rewriter.py**

```python
import pytest
from src.graphrag.query_rewriter import QueryRewriter


def test_query_rewriter_import():
    assert QueryRewriter is not None


def test_rewriter_initialization():
    class MockLLM:
        def generate(self, prompt, **kwargs):
            return '[\"意图1\", \"意图2\", \"意图3\"]'
    
    rewriter = QueryRewriter(MockLLM())
    assert rewriter.llm is not None
```

- [ ] **Step 4: 运行测试**

```bash
python -m pytest tests/graphrag/test_query_rewriter.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/graphrag/query_rewriter.py tests/graphrag/
git commit -m feat: add Query Rewriter module
```

---

### Task 5: GraphRAG - Multi-Path Retriever

**Files:**
- Create: `src/graphrag/retriever.py`
- Create: `tests/graphrag/test_retriever.py`

- [ ] **Step 1: 创建 src/graphrag/retriever.py**

```python
from src.kg.client import Neo4jClient, MilvusClient
from src.kg.models import EvidenceNode, EvidenceGraph
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class MultiPathRetriever:
    def __init__(self, neo4j_client: Neo4jClient, milvus_client: Optional[MilvusClient] = None):
        self.neo4j = neo4j_client
        self.milvus = milvus_client
    
    async def retrieve(self, intents: list[str], top_k: int = 30) -> EvidenceGraph:
        all_nodes = []
        
        for intent in intents:
            component_nodes = self._retrieve_components(intent, top_k // 3)
            document_nodes = self._retrieve_documents(intent, top_k // 3)
            term_nodes = self._retrieve_terms(intent, top_k // 3)
            
            all_nodes.extend(component_nodes)
            all_nodes.extend(document_nodes)
            all_nodes.extend(term_nodes)
        
        deduplicated = self._deduplicate_nodes(all_nodes, top_k)
        
        subgraph = self.neo4j.get_subgraph([n.id for n in deduplicated], depth=2)
        evidence_graph = EvidenceGraph(nodes=deduplicated, edges=subgraph.get('edges', []))
        
        logger.info(fRetrieved {len(deduplicated)} unique nodes for {len(intents)} intents)
        return evidence_graph
    
    def _retrieve_components(self, query: str, top_k: int) -> list[EvidenceNode]:
        results = self.neo4j.search_components(query, top_k)
        return [
            EvidenceNode(
                node_type='Component',
                id=r.get('id', ''),
                name=r.get('name', ''),
                properties=r,
                text=f部件: {r.get('name')}, 适用型号: {r.get('battery_model')}, 工具: {r.get('tool_required')}, 安全等级: {r.get('safety_level')}
            )
            for r in results
        ]
    
    def _retrieve_documents(self, query: str, top_k: int) -> list[EvidenceNode]:
        results = self.neo4j.search_documents(query, top_k)
        return [
            EvidenceNode(
                node_type='Document',
                id=r.get('doc_id', ''),
                name=r.get('title', ''),
                properties=r,
                text=f文档: {r.get('title')}, 来源: {r.get('source')}, 类型: {r.get('source_type')}\n{r.get('content', '')[:200]}
            )
            for r in results
        ]
    
    def _retrieve_terms(self, query: str, top_k: int) -> list[EvidenceNode]:
        results = self.neo4j.search_terms(query, top_k)
        return [
            EvidenceNode(
                node_type='Term',
                id=r.get('term_id', ''),
                name=r.get('term_id', ''),
                properties=r,
                text=f术语: {r.get('term_id')}, 定义: {r.get('definition')}, 单位: {r.get('units')}
            )
            for r in results
        ]
    
    def _deduplicate_nodes(self, nodes: list[EvidenceNode], top_k: int) -> list[EvidenceNode]:
        seen = {}
        for node in nodes:
            if node.id not in seen:
                seen[node.id] = node
        
        return list(seen.values())[:top_k]
```

- [ ] **Step 2: 创建 tests/graphrag/test_retriever.py**

```python
import pytest
from src.graphrag.retriever import MultiPathRetriever


def test_retriever_import():
    assert MultiPathRetriever is not None
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/graphrag/test_retriever.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/graphrag/retriever.py tests/graphrag/
git commit -m feat: add Multi-Path Retriever module
```

---

### Task 6: GraphRAG - Evidence Ranker

**Files:**
- Create: `src/graphrag/ranker.py`
- Create: `tests/graphrag/test_ranker.py`

- [ ] **Step 1: 创建 src/graphrag/ranker.py**

```python
from src.kg.models import EvidenceNode
from typing import list
import logging

logger = logging.getLogger(__name__)


class EvidenceRanker:
    def __init__(self, text_weight: float = 0.5, graph_weight: float = 0.3, recency_weight: float = 0.2):
        self.text_weight = text_weight
        self.graph_weight = graph_weight
        self.recency_weight = recency_weight
    
    def rank(self, nodes: list[EvidenceNode], query: str) -> list[EvidenceNode]:
        scored = []
        
        for node in nodes:
            text_score = self._calculate_text_score(node, query)
            graph_score = self._calculate_graph_score(node)
            recency_score = self._calculate_recency_score(node)
            
            final_score = (
                self.text_weight * text_score +
                self.graph_weight * graph_score +
                self.recency_weight * recency_score
            )
            
            scored.append((node, final_score))
        
        sorted_nodes = sorted(scored, key=lambda x: x[1], reverse=True)
        ranked = [node for node, score in sorted_nodes]
        
        logger.info(fRanked {len(ranked)} evidence nodes')
        return ranked
    
    def _calculate_text_score(self, node: EvidenceNode, query: str) -> float:
        query_lower = query.lower()
        text_lower = node.text.lower()
        
        if query_lower in text_lower:
            return 1.0
        
        query_words = set(query_lower.split())
        text_words = set(text_lower.split())
        overlap = len(query_words & text_words)
        
        return min(overlap / max(len(query_words), 1), 1.0)
    
    def _calculate_graph_score(self, node: EvidenceNode) -> float:
        degree = len(node.relationships)
        return min(degree / 10.0, 1.0)
    
    def _calculate_recency_score(self, node: EvidenceNode) -> float:
        return node.properties.get('recency_score', 0.8)
```

- [ ] **Step 2: 创建 tests/graphrag/test_ranker.py**

```python
import pytest
from src.graphrag.ranker import EvidenceRanker


def test_ranker_import():
    assert EvidenceRanker is not None
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/graphrag/test_ranker.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/graphrag/ranker.py tests/graphrag/
git commit -m feat: add Evidence Ranker module
```

---

### Task 7: GraphRAG - Generator

**Files:**
- Create: `src/graphrag/generator.py`

- [ ] **Step 1: 创建 src/graphrag/generator.py**

```python
from src.utils.llm_client import LLMClient
from src.kg.models import EvidenceGraph
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PlanGenerator:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
    
    def generate(self, query: str, evidence: EvidenceGraph, 
                 battery_model: str, context: list[str] = None) -> dict:
        context_str = ', '.join(context) if context else '无'
        evidence_text = evidence.to_text()
        
        prompt = f'''任务: 为电池型号 {battery_model} 生成拆卸方案
用户查询: {query}
工作环境上下文: {context_str}

参考证据:
{evidence_text}

请生成拆卸步骤列表，格式如下:
- 步骤序号
- 部件名称
- 具体操作
- 所需工具
- 安全等级
- 证据来源

请以JSON数组格式返回，每个元素包含: id, component, action, tool, safety_level, evidence'''

        try:
            result = self.llm.generate_json(prompt, ['steps'])
            logger.info(fGenerated plan with {len(result.get('steps', []))} steps')
            return result
        except Exception as e:
            logger.error(fPlan generation failed: {e})
            return {'error': str(e), 'steps': []}
    
    def regenerate(self, query: str, evidence: EvidenceGraph, 
                   battery_model: str, context: list[str] = None) -> dict:
        return self.generate(query, evidence, battery_model, context)
```

- [ ] **Step 2: Commit**

```bash
git add src/graphrag/generator.py
git commit -m feat: add Plan Generator module
```

---

### Task 8: GraphRAG - Feedback Loop

**Files:**
- Create: `src/graphrag/feedback.py`

- [ ] **Step 1: 创建 src/graphrag/feedback.py**

```python
from src.graphrag.retriever import MultiPathRetriever
from src.graphrag.ranker import EvidenceRanker
from src.graphrag.generator import PlanGenerator
from src.kg.models import EvidenceGraph
import logging

logger = logging.getLogger(__name__)


class FeedbackLoop:
    def __init__(self, retriever: MultiPathRetriever, ranker: EvidenceRanker,
                 generator: PlanGenerator, max_iterations: int = 3):
        self.retriever = retriever
        self.ranker = ranker
        self.generator = generator
        self.max_iterations = max_iterations
    
    async def refine(self, query: str, initial_plan: dict, evidence: EvidenceGraph,
                     battery_model: str, context: list[str] = None) -> tuple[dict, EvidenceGraph, int]:
        iteration_count = 0
        
        for iteration in range(self.max_iterations):
            iteration_count += 1
            logger.info(fFeedback iteration {iteration_count}')
            
            missing_evidence = self._extract_missing_evidence(initial_plan, evidence)
            
            if not missing_evidence:
                logger.info(fNo missing evidence, stopping at iteration {iteration_count}')
                break
            
            new_nodes = await self._retrieve_missing(missing_evidence)
            evidence.expand(new_nodes)
            
            initial_plan = self.generator.regenerate(query, evidence, battery_model, context)
        
        return initial_plan, evidence, iteration_count
    
    def _extract_missing_evidence(self, plan: dict, evidence: EvidenceGraph) -> list[str]:
        missing = []
        plan_steps = plan.get('steps', [])
        
        evidence_ids = {node.id for node in evidence.nodes}
        
        for step in plan_steps:
            step_evidence = step.get('evidence', [])
            if not step_evidence or all(e not in evidence_ids for e in step_evidence):
                component = step.get('component', '')
                if component:
                    missing.append(component)
        
        return missing[:10]
    
    async def _retrieve_missing(self, missing_items: list[str]) -> list:
        all_nodes = []
        for item in missing_items:
            components = self.retriever._retrieve_components(item, 5)
            all_nodes.extend(components)
        return all_nodes
```

- [ ] **Step 2: Commit**

```bash
git add src/graphrag/feedback.py
git commit -m feat: add Feedback Loop module
```

---

### Task 9: GraphRAG - Planner Orchestrator

**Files:**
- Create: `src/graphrag/planner.py`

- [ ] **Step 1: 创建 src/graphrag/planner.py**

```python
from src.graphrag.query_rewriter import QueryRewriter
from src.graphrag.retriever import MultiPathRetriever
from src.graphrag.ranker import EvidenceRanker
from src.graphrag.generator import PlanGenerator
from src.graphrag.feedback import FeedbackLoop
from src.kg.models import EvidenceGraph
from src.utils.llm_client import LLMClient
import logging
import time

logger = logging.getLogger(__name__)


class Planner:
    def __init__(self, llm_client: LLMClient, retriever: MultiPathRetriever):
        self.rewriter = QueryRewriter(llm_client)
        self.retriever = retriever
        self.ranker = EvidenceRanker()
        self.generator = PlanGenerator(llm_client)
        self.feedback = FeedbackLoop(retriever, self.ranker, self.generator)
    
    async def plan(self, query: str, battery_model: str, context: list[str] = None,
                   debug: bool = False) -> dict:
        trace = {'timing': {}} if debug else None
        
        start = time.time()
        if debug:
            trace['start_time'] = start
        
        rewritten_intents = self.rewriter.rewrite(query, context)
        if debug:
            trace['rewritten_queries'] = rewritten_intents
            trace['timing']['rewrite_ms'] = int((time.time() - start) * 1000)
        
        start = time.time()
        evidence_graph = await self.retriever.retrieve(rewritten_intents)
        if debug:
            trace['retrieval_nodes'] = len(evidence_graph.nodes)
            trace['timing']['retrieve_ms'] = int((time.time() - start) * 1000)
        
        ranked_evidence = self.ranker.rank(evidence_graph.nodes, query)
        evidence_graph.nodes = ranked_evidence
        
        start = time.time()
        initial_plan = self.generator.generate(query, evidence_graph, battery_model, context)
        if debug:
            trace['timing']['generate_ms'] = int((time.time() - start) * 1000)
        
        start = time.time()
        final_plan, evidence_graph, iterations = await self.feedback.refine(
            query, initial_plan, evidence_graph, battery_model, context
        )
        
        if debug:
            trace['timing']['feedback_ms'] = int((time.time() - start) * 1000)
            trace['iteration_count'] = iterations
            trace['final_evidence_count'] = len(evidence_graph.nodes)
            trace['timing']['total_ms'] = int((time.time() - trace['start_time']) * 1000)
            trace['evidence_graph'] = {
                'nodes': [{'id': n.id, 'type': n.node_type, 'name': n.name} for n in evidence_graph.nodes[:20]],
                'edges': evidence_graph.edges[:20]
            }
        
        result = {
            'code': 0,
            'message': 'Success',
            'data': {
                'steps': final_plan.get('steps', [])
            }
        }
        
        if debug:
            result['data']['trace'] = trace
        
        return result
```

- [ ] **Step 2: 创建 tests/graphrag/test_planner.py**

```python
import pytest
from src.graphrag.planner import Planner


def test_planner_import():
    assert Planner is not None
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/graphrag/test_planner.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/graphrag/planner.py tests/graphrag/
git commit -m feat: add Planner orchestrator
```

---

### Task 10: API层

**Files:**
- Create: `src/api/__init__.py`
- Create: `src/api/schemas.py`
- Create: `src/api/routes.py`
- Create: `src/api/middleware.py`
- Create: `src/main.py`
- Create: `tests/api/test_routes.py`

- [ ] **Step 1: 创建 src/api/__init__.py**

```python
```

- [ ] **Step 2: 创建 src/api/schemas.py**

```python
from pydantic import BaseModel
from typing import Optional, list


class PlanRequest(BaseModel):
    battery_model: str
    context: list[str] = []
    debug: bool = False


class Step(BaseModel):
    id: int
    component: str
    action: str
    tool: list[str] = []
    evidence: list[str] = []
    confidence: Optional[float] = None
    safety_level: Optional[int] = None


class PlanResponse(BaseModel):
    code: int = 0
    message: str = 'Success'
    data: Optional[dict] = None


class HealthResponse(BaseModel):
    status: str
    neo4j: str
    milvus: str
    llm: str


class ErrorResponse(BaseModel):
    code: int
    message: str
    detail: Optional[str] = None
```

- [ ] **Step 3: 创建 src/api/middleware.py**

```python
from fastapi import Request
from src.logs import logger
import time


async def logging_middleware(request: Request, call_next):
    start_time = time.time()
    
    logger.info(f{request.method} {request.url.path})
    
    response = await call_next(request)
    
    duration = int((time.time() - start_time) * 1000)
    logger.info(f{request.method} {request.url.path} - {response.status_code} - {duration}ms)
    
    return response
```

- [ ] **Step 4: 创建 src/api/routes.py**

```python
from fastapi import APIRouter, HTTPException, Depends
from src.api.schemas import PlanRequest, PlanResponse, HealthResponse
from src.kg.client import Neo4jClient, MilvusClient
from src.graphrag.planner import Planner
from src.utils.llm_client import LLMClient
from src.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

neo4j_client = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
milvus_client = MilvusClient(settings.milvus_host, settings.milvus_port) if hasattr(settings, 'milvus_host') else None
llm_client = LLMClient(settings.openai_api_key, settings.openai_base_url, settings.model, settings.temperature, settings.max_tokens)

retriever = MultiPathRetriever(neo4j_client, milvus_client)
planner = Planner(llm_client, retriever)


@router.post('/api/v1/disassembly/plan', response_model=PlanResponse)
async def create_plan(request: PlanRequest):
    try:
        result = await planner.plan(
            query=f拆卸{battery_model}型号电池,
            battery_model=request.battery_model,
            context=request.context,
            debug=request.debug
        )
        return result
    except Exception as e:
        logger.error(fPlan creation failed: {e}')
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/api/v1/health', response_model=HealthResponse)
async def health_check():
    neo4j_status = 'connected' if neo4j_client.verify_connectivity() else 'disconnected'
    milvus_status = 'connected' if milvus_client and milvus_client.collection else 'not_configured'
    llm_status = 'available'
    
    return HealthResponse(
        status='healthy' if neo4j_status == 'connected' else 'degraded',
        neo4j=neo4j_status,
        milvus=milvus_status,
        llm=llm_status
    )
```

- [ ] **Step 5: 创建 src/main.py**

```python
from fastapi import FastAPI
from src.api.routes import router
from src.api.middleware import logging_middleware
from src.logs import logger

app = FastAPI(title='动力电池拆卸知识图谱推理系统', version='1.0.0')

app.middleware('http')(logging_middleware)

app.include_router(router)


@app.on_event('shutdown')
async def shutdown_event():
    logger.info('Shutting down application')
    neo4j_client.close()
    if milvus_client:
        milvus_client.close()


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
```

- [ ] **Step 6: 创建 tests/api/test_routes.py**

```python
import pytest
from fastapi.testclient import TestClient


def test_routes_import():
    from src.api import routes
    assert routes.router is not None
```

- [ ] **Step 7: 运行测试**

```bash
python -m pytest tests/api/test_routes.py -v
```

- [ ] **Step 8: Commit**

```bash
git add src/api/ src/main.py tests/api/
git commit -m feat: add FastAPI layer
```

---

## 验收标准

- [ ] Task 1: requirements.txt, config.py, logs.py 创建完成
- [ ] Task 2: Neo4j和Milvus客户端封装完成
- [ ] Task 3: LLM客户端封装完成
- [ ] Task 4: Query Rewriter模块完成
- [ ] Task 5: Multi-Path Retriever模块完成
- [ ] Task 6: Evidence Ranker模块完成
- [ ] Task 7: Plan Generator模块完成
- [ ] Task 8: Feedback Loop模块完成
- [ ] Task 9: Planner编排器完成
- [ ] Task 10: API层完整实现

---

## 总结

**计划完成文件:** `docs/superpowers/plans/2026-04-14-phase1-implementation-plan.md`

**下一步执行选项：**

**1. Subagent-Driven (推荐)** - 每个任务由独立子代理执行，任务间进行审查和快速迭代

**2. Inline Execution** - 使用executing-plans技能在此会话中执行任务，设置检查点进行审查

**你选择哪种方式？**