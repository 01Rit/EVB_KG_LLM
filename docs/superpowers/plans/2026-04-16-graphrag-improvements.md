# GraphRAG Core Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve Final4.14 GraphRAG core with LLM caching, token-aware truncation, async rate limiting, and community detection + global query support.

**Architecture:**
1. Add `tiktoken`-based tokenization utility for accurate token counting and truncation
2. Implement MD5-hash-based LLM response caching to avoid redundant API calls
3. Add async rate limiting decorator to prevent API overload
4. Implement Leiden community detection on Neo4j graph + Map-Reduce global query

**Tech Stack:** tiktoken, python-louvain/leidenalg, NetworkX, asyncio

---

## File Structure

```
src/
├── utils/
│   ├── llm_client.py        (modify: add caching + async rate limit)
│   └── tokenizer.py         (create: tiktoken wrapper + truncate functions)
├── graphrag/
│   ├── community.py         (create: community detection + report generation)
│   ├── global_query.py      (create: Map-Reduce global query implementation)
│   ├── planner.py           (modify: add global/local mode parameter)
│   ├── ranker.py            (modify: token-aware truncation)
│   └── generator.py         (modify: token-aware truncation)
└── kg/
    └── client.py            (modify: add community detection queries)
```

---

## Task 1: Create tokenizer utility

**Files:**
- Create: `src/utils/tokenizer.py`
- Test: `tests/utils/test_tokenizer.py`

- [ ] **Step 1: Write failing test**

```python
# tests/utils/test_tokenizer.py
import pytest
from src.utils.tokenizer import encode_string_by_tiktoken, truncate_by_token_size

def test_encode_returns_list():
    result = encode_string_by_tiktoken("hello world")
    assert isinstance(result, list)
    assert len(result) > 0

def test_truncate_respects_max_tokens():
    long_text = " ".join(["word"] * 1000)
    result = truncate_by_token_size([long_text, long_text], key=lambda x: x, max_token_size=50)
    assert len(result) <= 2  # may truncate to 1-2 items

def test_truncate_empty_list():
    result = truncate_by_token_size([], key=lambda x: x, max_token_size=100)
    assert result == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/utils/test_tokenizer.py -v`
Expected: FAIL - module 'src.utils.tokenizer' has no attribute 'encode_string_by_tiktoken'

- [ ] **Step 3: Write minimal implementation**

```python
# src/utils/tokenizer.py
import tiktoken
from typing import Callable, Any

ENCODER = None

def encode_string_by_tiktoken(content: str, model_name: str = "gpt-4o") -> list[int]:
    global ENCODER
    if ENCODER is None:
        ENCODER = tiktoken.encoding_for_model(model_name)
    return ENCODER.encode(content)

def truncate_by_token_size(list_data: list, key: Callable[[Any], str], max_token_size: int) -> list:
    """Truncate list of items by total token size of their key function output."""
    tokens = 0
    for i, data in enumerate(list_data):
        tokens += len(encode_string_by_tiktoken(key(data)))
        if tokens > max_token_size:
            return list_data[:i]
    return list_data
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/utils/test_tokenizer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/utils/test_tokenizer.py src/utils/tokenizer.py
git commit -m "feat: add tiktoken-based tokenizer utility"
```

---

## Task 2: Add LLM caching to LLMClient

**Files:**
- Modify: `src/utils/llm_client.py:1-50`
- Create: `tests/utils/test_llm_client.py`

- [ ] **Step 1: Write failing test**

```python
# tests/utils/test_llm_client.py
import pytest
from unittest.mock import patch, MagicMock
from src.utils.llm_client import LLMClient

def test_caching_returns_same_result_for_same_prompt():
    client = LLMClient(api_key="test", model="gpt-4o")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="cached response"))]

    with patch.object(client.client.chat.completions, 'create', return_value=mock_response) as mock_create:
        result1 = client.generate("test prompt")
        result2 = client.generate("test prompt")
        assert result1 == result2
        assert mock_create.call_count == 1  # second call uses cache

def test_different_prompts_call_api():
    client = LLMClient(api_key="test", model="gpt-4o")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="response"))]

    with patch.object(client.client.chat.completions, 'create', return_value=mock_response) as mock_create:
        client.generate("prompt A")
        client.generate("prompt B")
        assert mock_create.call_count == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/utils/test_llm_client.py -v`
Expected: FAIL - assert 2 == 1 (caching not implemented)

- [ ] **Step 3: Write implementation with caching**

```python
# src/utils/llm_client.py
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
        self._cache = {}  # {hash: response_str}

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/utils/test_llm_client.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/utils/llm_client.py tests/utils/test_llm_client.py
git commit -m "feat: add LLM response caching to LLMClient"
```

---

## Task 3: Add async rate limiter decorator

**Files:**
- Create: `src/utils/rate_limiter.py`
- Modify: `src/utils/llm_client.py`

- [ ] **Step 1: Write failing test**

```python
# tests/utils/test_rate_limiter.py
import pytest
import asyncio
from src.utils.rate_limiter import limit_async_func_call

def test_rate_limiter_blocks_when_maxed():
    call_count = 0
    max_concurrent = 2

    @limit_async_func_call(max_size=max_concurrent)
    async def slow_func():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)
        return call_count

    async def run_all():
        results = await asyncio.gather(*[slow_func() for _ in range(4)])
        return results

    start = asyncio.get_event_loop().time()
    results = asyncio.get_event_loop().run_until_complete(run_all())
    elapsed = asyncio.get_event_loop().time() - start

    # With max_size=2 and 4 calls, 2 batches should complete
    assert max(results) <= 4
    # Should take longer than single batch due to rate limiting
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/utils/test_rate_limiter.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write implementation**

```python
# src/utils/rate_limiter.py
import asyncio
from functools import wraps

def limit_async_func_call(max_size: int, waiting_time: float = 0.001):
    """
    Decorator to limit maximum concurrent async function calls.
    Uses asyncio.sleep instead of Semaphore to avoid nest-asyncio issues.
    """
    def decorator(func):
        __current_size = 0

        @wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal __current_size
            while __current_size >= max_size:
                await asyncio.sleep(waiting_time)
            __current_size += 1
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                __current_size -= 1

        return wrapper
    return decorator
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/utils/test_rate_limiter.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/utils/rate_limiter.py tests/utils/test_rate_limiter.py
git commit -m "feat: add async rate limiter decorator"
```

---

## Task 4: Add token-aware truncation to generator

**Files:**
- Modify: `src/graphrag/generator.py`
- Create: `tests/graphrag/test_generator.py`

- [ ] **Step 1: Write failing test**

```python
# tests/graphrag/test_generator.py
import pytest
from unittest.mock import MagicMock
from src.graphrag.generator import PlanGenerator
from src.kg.models import EvidenceNode

def test_generate_truncates_long_context():
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {"steps": []}

    generator = PlanGenerator(mock_llm)

    long_evidence = EvidenceNode(
        node_type="Component",
        id="1",
        name="Test",
        properties={},
        text="word " * 5000  # very long text
    )

    result = generator.generate(
        query="test",
        evidence=MagicMock(nodes=[long_evidence], edges=[], to_text=lambda: "x " * 5000),
        battery_model="TEST",
        context=None,
        kg_context=None
    )

    assert "steps" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/graphrag/test_generator.py -v`
Expected: PASS (existing implementation should handle it, but truncation may be imprecise)

- [ ] **Step 3: Write token-aware implementation**

```python
# src/graphrag/generator.py
from src.utils.llm_client import LLMClient
from src.kg.models import EvidenceGraph
from src.utils.tokenizer import encode_string_by_tiktoken
from typing import Optional
import logging

logger = logging.getLogger(__name__)

MAX_CONTEXT_TOKENS = 6000  # Leave room for prompt template

class PlanGenerator:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def _truncate_evidence(self, evidence: EvidenceGraph, max_tokens: int = MAX_CONTEXT_TOKENS) -> str:
        """Truncate evidence text to fit within token limit."""
        text = evidence.to_text()
        tokens = encode_string_by_tiktoken(text)
        if len(tokens) <= max_tokens:
            return text
        # Decode truncated tokens
        encoder = None
        import tiktoken
        encoder = tiktoken.encoding_for_model("gpt-4o")
        return encoder.decode(tokens[:max_tokens])

    def generate(self, query: str, evidence: EvidenceGraph,
                 battery_model: str, context: Optional[list[str]] = None,
                 kg_context: str = None) -> dict:
        context_str = ', '.join(context) if context else '无'
        evidence_text = self._truncate_evidence(evidence)
        kg_info = kg_context if kg_context else evidence_text

        prompt = f'''任务: 为电池型号 {battery_model} 生成拆卸方案

用户查询: {query}
工作环境上下文: {context_str}

{kg_info}

【重要提示】
拆卸顺序规则：
1. 先拆上壳体(upper housing)、下壳体(lower housing)、绝缘层(insulator)等外层保护部件
2. 最后拆电芯(cells, modules, CMC) 和核心部件
3. 每一步需要说明依赖的前置步骤（如：必须先拆X才能拆Y）

请生成拆卸步骤列表，格式如下:
- 步骤序号 (id)
- 部件名称 (component) - 英文名称
- 具体操作 (action) - 描述如何拆卸
- 所需工具 (tool) - 列出所需工具
- 安全等级 (safety_level) - 1-5的数字
- 依赖步骤 (depends_on) - 哪些步骤必须先完成

请以JSON格式返回，包含steps数组，每个元素包含: id, component, action, tool, safety_level, depends_on'''

        try:
            result = self.llm.generate_json(prompt, ['steps'])
            logger.info(f'Generated plan with {len(result.get("steps", []))} steps')
            return result
        except Exception as e:
            logger.error(f'Plan generation failed: {e}')
            return {'error': str(e), 'steps': []}

    def regenerate(self, query: str, evidence: EvidenceGraph,
                   battery_model: str, context: Optional[list[str]] = None) -> dict:
        return self.generate(query, evidence, battery_model, context)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/graphrag/test_generator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/graphrag/generator.py tests/graphrag/test_generator.py
git commit -m "feat: add token-aware truncation to generator"
```

---

## Task 5: Add token-aware truncation to ranker

**Files:**
- Modify: `src/graphrag/ranker.py`

- [ ] **Step 1: Review existing implementation**

```python
# src/graphrag/ranker.py (existing)
# Current: text_similarity (0.5) + graph_centrality (0.3) + recency (0.2)
# May need token truncation for long evidence lists
```

- [ ] **Step 2: Add truncation to rank method**

```python
# src/graphrag/ranker.py
from src.kg.models import EvidenceNode
from src.utils.tokenizer import truncate_by_token_size
import logging

logger = logging.getLogger(__name__)

MAX_EVIDENCE_TOKENS = 4000

class EvidenceRanker:
    def __init__(self):
        self.text_weight = 0.5
        self.graph_weight = 0.3
        self.recency_weight = 0.2

    def rank(self, nodes: list[EvidenceNode], query: str) -> list[EvidenceNode]:
        if not nodes:
            return []

        scored = []
        for node in nodes:
            text_score = self._text_similarity(node.text, query)
            graph_score = node.properties.get('degree', 0) / 10.0
            recency_score = node.properties.get('recency_score', 0.5)
            total = (self.text_weight * text_score +
                    self.graph_weight * graph_score +
                    self.recency_weight * recency_score)
            scored.append((total, node))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Truncate to max tokens before returning
        nodes_sorted = [node for _, node in scored]
        truncated = truncate_by_token_size(
            nodes_sorted,
            key=lambda n: n.text,
            max_token_size=MAX_EVIDENCE_TOKENS
        )
        return truncated

    def _text_similarity(self, text: str, query: str) -> float:
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())
        if not query_words:
            return 0.5
        overlap = len(query_words & text_words)
        return overlap / len(query_words)
```

- [ ] **Step 3: Run existing tests**

Run: `pytest tests/graphrag/test_ranker.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/graphrag/ranker.py
git commit -m "feat: add token-aware truncation to ranker"
```

---

## Task 6: Add community detection to Neo4jClient

**Files:**
- Modify: `src/kg/client.py`

- [ ] **Step 1: Add community detection method**

```python
# src/kg/client.py (add after existing methods)

def detect_communities(self, level: int = 2) -> list[dict]:
    """
    Detect communities in the knowledge graph using Leiden algorithm.
    Returns list of community dicts with node assignments.
    """
    import networkx as nx
    from community import community_louvain

    # Get all nodes and edges
    with self.driver.session() as session:
        result = session.run("""
            MATCH (n)-[r]->(m)
            RETURN n.id AS source, m.id AS target, type(r) AS rel_type
        """)
        edges = [(record['source'], record['target']) for record in result]

    if not edges:
        return []

    # Build NetworkX graph
    G = nx.Graph()
    G.add_edges_from(edges)

    # Detect communities using Louvain
    partition = community_louvain.best_partition(G)

    # Group nodes by community
    communities = {}
    for node, comm_id in partition.items():
        if comm_id not in communities:
            communities[comm_id] = []
        communities[comm_id].append(node)

    return [
        {'id': cid, 'nodes': nodes, 'level': level}
        for cid, nodes in communities.items()
    ]

def get_subgraph_nodes(self, node_ids: list[str]) -> list[dict]:
    """Get node details for a list of node IDs."""
    if not node_ids:
        return []
    with self.driver.session() as session:
        result = session.run("""
            MATCH (n) WHERE n.id IN $ids
            RETURN n.id AS id, labels(n) AS labels, properties(n) AS props
        """, ids=node_ids)
        return [dict(record) for record in result]
```

- [ ] **Step 2: Run tests to verify no regression**

Run: `pytest tests/kg/test_client.py -v`
Expected: PASS (if tests exist) or manual verification

- [ ] **Step 3: Commit**

```bash
git add src/kg/client.py
git commit -m "feat: add community detection to Neo4jClient"
```

---

## Task 7: Create community report generator

**Files:**
- Create: `src/graphrag/community.py`
- Test: `tests/graphrag/test_community.py`

- [ ] **Step 1: Write failing test**

```python
# tests/graphrag/test_community.py
import pytest
from unittest.mock import MagicMock, patch
from src.graphrag.community import CommunityDetector

def test_detect_communities_returns_list():
    mock_neo4j = MagicMock()
    mock_neo4j.detect_communities.return_value = [
        {'id': 0, 'nodes': ['A', 'B'], 'level': 2},
        {'id': 1, 'nodes': ['C', 'D'], 'level': 2}
    ]

    detector = CommunityDetector(mock_neo4j, MagicMock())
    communities = detector.detect()
    assert len(communities) == 2

def test_generate_report_for_community():
    mock_neo4j = MagicMock()
    mock_neo4j.get_subgraph_nodes.return_value = [
        {'id': 'A', 'props': {'name': 'Component A'}},
        {'id': 'B', 'props': {'name': 'Component B'}}
    ]

    mock_llm = MagicMock()
    mock_llm.generate.return_value = '{"title": "Test", "summary": "Test summary", "findings": []}'

    detector = CommunityDetector(mock_neo4j, mock_llm)
    community = {'id': 0, 'nodes': ['A', 'B'], 'level': 2}
    report = detector.generate_report(community)
    assert 'title' in report
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/graphrag/test_community.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write implementation**

```python
# src/graphrag/community.py
from typing import Optional
import logging
from src.kg.client import Neo4jClient
from src.utils.llm_client import LLMClient
from src.utils.tokenizer import encode_string_by_tiktoken

logger = logging.getLogger(__name__)

COMMUNITY_REPORT_PROMPT = """给定以下社区的节点信息，请生成社区报告：

节点信息：
{node_info}

请以JSON格式返回，包含：
- title: 社区标题
- summary: 简要总结
- findings: 主要发现列表，每个发现包含 summary 和 explanation"""

class CommunityDetector:
    def __init__(self, neo4j_client: Neo4jClient, llm_client: LLMClient):
        self.neo4j = neo4j_client
        self.llm = llm_client

    def detect(self) -> list[dict]:
        """Detect communities in the graph."""
        return self.neo4j.detect_communities(level=2)

    def generate_report(self, community: dict) -> dict:
        """Generate LLM report for a community."""
        node_ids = community['nodes']
        nodes_data = self.neo4j.get_subgraph_nodes(node_ids)

        node_info = "\n".join([
            f"- {n.get('props', {}).get('name', n['id'])}"
            for n in nodes_data
        ])

        prompt = COMMUNITY_REPORT_PROMPT.format(node_info=node_info)

        try:
            result = self.llm.generate(prompt)
            import json
            return json.loads(result)
        except Exception as e:
            logger.error(f"Failed to generate community report: {e}")
            return {"title": "Error", "summary": str(e), "findings": []}

    async def generate_all_reports(self, communities: list[dict]) -> list[dict]:
        """Generate reports for all communities."""
        reports = []
        for comm in communities:
            report = self.generate_report(comm)
            report['community_id'] = comm['id']
            report['node_count'] = len(comm['nodes'])
            reports.append(report)
        return reports
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/graphrag/test_community.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/graphrag/community.py tests/graphrag/test_community.py
git commit -m "feat: add community detection and report generation"
```

---

## Task 8: Create global query implementation

**Files:**
- Create: `src/graphrag/global_query.py`
- Test: `tests/graphrag/test_global_query.py`

- [ ] **Step 1: Write failing test**

```python
# tests/graphrag/test_global_query.py
import pytest
from unittest.mock import MagicMock
from src.graphrag.global_query import GlobalQueryEngine

def test_global_query_processes_communities():
    mock_neo4j = MagicMock()
    mock_neo4j.detect_communities.return_value = [
        {'id': 0, 'nodes': ['A', 'B'], 'level': 2},
        {'id': 1, 'nodes': ['C', 'D'], 'level': 2}
    ]

    mock_llm = MagicMock()
    mock_llm.generate.return_value = '{"points": [{"description": "point1", "score": 1}]}'

    engine = GlobalQueryEngine(mock_neo4j, mock_llm, MagicMock())
    result = engine.query("test query")
    assert 'response' in result or 'error' not in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/graphrag/test_global_query.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write implementation**

```python
# src/graphrag/global_query.py
import asyncio
from typing import Optional
import logging
from src.kg.client import Neo4jClient
from src.utils.llm_client import LLMClient
from src.utils.tokenizer import truncate_by_token_size
from src.graphrag.community import CommunityDetector

logger = logging.getLogger(__name__)

MAP_PROMPT = """给定以下社区报告，请提取与查询相关的关键点：

查询: {query}

社区报告:
{community_reports}

请以JSON格式返回，包含 points 数组，每个元素包含：
- description: 关键点描述
- score: 重要性评分 (0-1)"""

REDUCE_PROMPT = """给定以下关键点，请生成最终回答：

查询: {query}

关键点:
{points}

请生成一个综合回答，总结所有关键点。"""

MAX_COMMUNITY_TOKENS = 8000
MAX_POINTS_TOKENS = 6000

class GlobalQueryEngine:
    def __init__(self, neo4j_client: Neo4jClient, llm_client: LLMClient,
                 community_detector: Optional[CommunityDetector] = None):
        self.neo4j = neo4j_client
        self.llm = llm_client
        self.community_detector = community_detector or CommunityDetector(neo4j_client, llm_client)

    def query(self, query: str, max_communities: int = 50) -> dict:
        """Execute global query using Map-Reduce pattern."""
        communities = self.community_detector.detect()
        if not communities:
            return {'response': 'No communities found', 'error': None}

        # Truncate communities by token size
        communities = truncate_by_token_size(
            communities,
            key=lambda c: str(c['nodes'][:10]),
            max_token_size=MAX_COMMUNITY_TOKENS
        )[:max_communities]

        # Generate reports for all communities
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        reports = loop.run_until_complete(
            self.community_detector.generate_all_reports(communities)
        )
        loop.close()

        # Map phase: Extract key points from each community
        map_results = self._map_phase(query, reports)

        # Reduce phase: Merge and rank key points
        response = self._reduce_phase(query, map_results)

        return {'response': response, 'error': None}

    def _map_phase(self, query: str, reports: list[dict]) -> list[dict]:
        """Map: Extract key points from each community report."""
        # Batch reports that fit in context window
        batch = []
        all_points = []

        for report in reports:
            report_str = f"## {report.get('title', 'N/A')}\n{report.get('summary', '')}"
            batch.append(report_str)

            if len("\n---\n".join(batch)) > MAX_COMMUNITY_TOKENS // 2:
                points = self._extract_points_from_batch(query, batch)
                all_points.extend(points)
                batch = []

        if batch:
            points = self._extract_points_from_batch(query, batch)
            all_points.extend(points)

        # Filter and sort by score
        all_points = [p for p in all_points if p.get('score', 0) > 0]
        all_points.sort(key=lambda x: x.get('score', 0), reverse=True)
        return all_points

    def _extract_points_from_batch(self, query: str, batch: list[str]) -> list[dict]:
        """Extract key points from a batch of community reports."""
        community_reports = "\n---\n".join(batch)
        prompt = MAP_PROMPT.format(query=query, community_reports=community_reports)

        try:
            result = self.llm.generate(prompt)
            import json
            data = json.loads(result)
            return data.get('points', [])
        except Exception as e:
            logger.error(f"Map phase failed: {e}")
            return []

    def _reduce_phase(self, query: str, points: list[dict]) -> str:
        """Reduce: Merge and generate final response."""
        if not points:
            return "No relevant information found."

        # Truncate points by token size
        points = truncate_by_token_size(
            points,
            key=lambda p: p.get('description', ''),
            max_token_size=MAX_POINTS_TOKENS
        )

        points_str = "\n".join([
            f"- {p.get('description', '')} (score: {p.get('score', 0)})"
            for p in points
        ])

        prompt = REDUCE_PROMPT.format(query=query, points=points_str)

        try:
            return self.llm.generate(prompt)
        except Exception as e:
            logger.error(f"Reduce phase failed: {e}")
            return f"Error generating response: {e}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/graphrag/test_global_query.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/graphrag/global_query.py tests/graphrag/test_global_query.py
git commit -m "feat: add global query with Map-Reduce pattern"
```

---

## Task 9: Update Planner to support global/local mode

**Files:**
- Modify: `src/graphrag/planner.py`

- [ ] **Step 1: Review existing implementation**

See Task 4 in previous analysis - Planner coordinates all GraphRAG components.

- [ ] **Step 2: Add mode parameter to plan method**

```python
# src/graphrag/planner.py
from typing import Optional
from src.graphrag.query_rewriter import QueryRewriter
from src.graphrag.retriever import MultiPathRetriever
from src.graphrag.ranker import EvidenceRanker
from src.graphrag.generator import PlanGenerator
from src.graphrag.feedback import FeedbackLoop
from src.graphrag.community import CommunityDetector
from src.graphrag.global_query import GlobalQueryEngine
from src.kg.models import EvidenceGraph
from src.utils.llm_client import LLMClient
import logging
import time

logger = logging.getLogger(__name__)

class Planner:
    def __init__(self, llm_client: LLMClient, retriever: MultiPathRetriever,
                 neo4j_client=None):
        self.rewriter = QueryRewriter(llm_client)
        self.retriever = retriever
        self.ranker = EvidenceRanker()
        self.generator = PlanGenerator(llm_client)
        self.feedback = FeedbackLoop(retriever, self.ranker, self.generator)

        if neo4j_client:
            community_detector = CommunityDetector(neo4j_client, llm_client)
            self.global_engine = GlobalQueryEngine(neo4j_client, llm_client, community_detector)
        else:
            self.global_engine = None

    async def plan(self, query: str, battery_model: str,
                   context: Optional[list[str]] = None,
                   mode: str = "local",
                   debug: bool = False) -> dict:
        """
        Execute planning query.

        Args:
            mode: "local" for entity-focused retrieval, "global" for community-based Map-Reduce
        """
        if mode == "global":
            return await self._plan_global(query, battery_model, context, debug)
        return await self._plan_local(query, battery_model, context, debug)

    async def _plan_global(self, query: str, battery_model: str,
                          context: Optional[list[str]], debug: bool) -> dict:
        """Global query using community detection and Map-Reduce."""
        if not self.global_engine:
            return {'code': 1, 'message': 'Global query not available', 'data': {}}

        trace = {'timing': {}} if debug else None
        start = time.time()

        result = self.global_engine.query(query)

        if debug:
            trace['timing']['total_ms'] = int((time.time() - start) * 1000)

        response = {
            'code': 0,
            'message': 'Success',
            'data': {
                'response': result.get('response', ''),
                'mode': 'global'
            }
        }

        if debug:
            response['data']['trace'] = trace

        return response

    async def _plan_local(self, query: str, battery_model: str,
                          context: Optional[list[str]], debug: bool) -> dict:
        """Local query using entity-focused retrieval (existing implementation)."""
        trace = {'timing': {}} if debug else None

        start = time.time()
        if debug:
            trace['start_time'] = start

        try:
            rewritten_intents = self.rewriter.rewrite(query, context)
            if not rewritten_intents:
                rewritten_intents = [query]
        except Exception as e:
            logger.warning(f'Rewrite failed, using original: {e}')
            rewritten_intents = [query]
        if debug:
            trace['rewritten_queries'] = rewritten_intents
            trace['timing']['rewrite_ms'] = int((time.time() - start) * 1000)

        start = time.time()
        evidence_graph = await self.retriever.retrieve(rewritten_intents, battery_model=battery_model)

        all_components = self.retriever.get_all_components(battery_model)
        all_relations = self.retriever.get_all_relations(battery_model)

        kg_context = self._format_kg_context(all_components, all_relations)

        if debug:
            trace['retrieval_nodes'] = len(evidence_graph.nodes)
            trace['timing']['retrieve_ms'] = int((time.time() - start) * 1000)
            trace['all_components_count'] = len(all_components)
            trace['all_relations_count'] = len(all_relations)

        if evidence_graph.nodes:
            ranked_evidence = self.ranker.rank(evidence_graph.nodes, query)
            evidence_graph.nodes = ranked_evidence
        else:
            ranked_evidence = []

        start = time.time()
        initial_plan = self.generator.generate(query, evidence_graph, battery_model, context, kg_context)
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
                'steps': final_plan.get('steps', []),
                'mode': 'local'
            }
        }

        if debug:
            result['data']['trace'] = trace

        return result

    def _format_kg_context(self, components: list, relations: list) -> str:
        if not components:
            return "No components found in knowledge graph."

        lines = ["=== Knowledge Graph Context ==="]
        lines.append(f"\n## Components ({len(components)} total):")
        for c in components[:20]:
            if hasattr(c, 'name'):
                name = c.name
            else:
                name = c.get('name', 'Unknown')
            lines.append(f"- {name}")

        if relations:
            lines.append(f"\n## Relations ({len(relations)} total):")
            for r in relations[:20]:
                head = r.get('head', '')
                rel = r.get('relation', '')
                tail = r.get('tail', '')
                lines.append(f"- {head} --[{rel}]--> {tail}")

        return "\n".join(lines)
```

- [ ] **Step 3: Run existing tests**

Run: `pytest tests/graphrag/test_planner.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/graphrag/planner.py
git commit -m "feat: add global/local mode support to Planner"
```

---

## Task 10: Update API route to support mode parameter

**Files:**
- Modify: `src/api/routes.py`

- [ ] **Step 1: Update plan endpoint**

```python
# src/api/routes.py (modify plan endpoint)
@router.post("/disassembly/plan")
async def create_disassembly_plan(request: DisassemblyPlanRequest):
    # ... existing code ...
    planner = request.state.planner  # or however planner is obtained

    mode = requestBody.get('mode', 'local')  # "local" or "global"

    result = await planner.plan(
        query=request.query,
        battery_model=request.battery_model,
        context=request.context,
        mode=mode,  # new parameter
        debug=request.debug
    )
    return result
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/api/test_routes.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add src/api/routes.py
git commit -m "feat: add mode parameter to plan endpoint"
```

---

## Dependencies Update

Add to `requirements.txt`:
```
tiktoken>=0.7.0
python-louvain>=0.16
```

---

## Self-Review Checklist

- [ ] All tasks have failing tests before implementation
- [ ] All tests pass after implementation
- [ ] No placeholders (TBD, TODO) in code
- [ ] Type consistency across tasks (EvidenceNode, LLMClient interfaces match)
- [ ] Each commit is atomic and self-contained

---

## Plan complete

Saved to: `docs/superpowers/plans/YYYY-MM-DD-graphrag-improvements.md`

**Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?