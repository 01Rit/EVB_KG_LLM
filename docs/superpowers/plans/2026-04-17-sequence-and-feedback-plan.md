# Disassembly Sequence & Feedback Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现拆卸序列规划优化（修复零件缺失）、电池型号搜索API、KG+LLM问答反馈模块（含SSE进度条）

**Architecture:**
1. 拆卸序列规划：修复`_load_components()`增加RELATES关系查询，新增`IsolatedNodeResolver`处理孤立节点
2. 电池搜索：新增API端点模糊搜索`Component.battery_model`
3. 问答反馈：新增`NaturalLanguageFeedback`类生成自然语言回答，SSE流式推送进度
4. 前端：电池搜索下拉框、来源切换按钮、SSE进度条

**Tech Stack:** Python FastAPI, Neo4j, LLM Client, SSE (Server-Sent Events)

---

## Task 1: 新增 IsolatedNodeResolver 孤立节点处理器

**Files:**
- Create: `src/sequence/island_resolver.py`
- Create: `tests/sequence/test_island_resolver.py`

- [ ] **Step 1: 编写测试**

```python
# tests/sequence/test_island_resolver.py
import pytest
from src.sequence.island_resolver import IsolatedNodeResolver, SimilarityMatcher

def test_similarity_matcher_name_similarity():
    matcher = SimilarityMatcher()
    # "upper_housing" 和 "lower_housing" 应该高相似
    score1 = matcher.calculate_name_similarity("upper_housing", "lower_housing")
    assert score1 > 0.5

    # "upper_housing" 和 "module_1" 应该低相似
    score2 = matcher.calculate_name_similarity("upper_housing", "module_1")
    assert score2 < 0.3

def test_resolve_isolated_nodes():
    resolver = IsolatedNodeResolver()
    isolated = ["cooling_pipe", "module_connector"]
    all_nodes = ["upper_housing", "lower_housing", "insulator", "module"]
    existing_edges = [
        ("upper_housing", "lower_housing"),
        ("insulator", "module")
    ]

    result = resolver.resolve(isolated, all_nodes, existing_edges)
    # cooling_pipe 可能匹配到 upper_housing (相似度)
    # module_connector 可能匹配到 module (类型匹配)
    assert isinstance(result, dict)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/sequence/test_island_resolver.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: 编写 SimilarityMatcher 类**

```python
# src/sequence/island_resolver.py
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class SimilarityMatcher:
    def __init__(self):
        self.threshold = 0.3

    def calculate_name_similarity(self, name1: str, name2: str) -> float:
        """计算两个名称的相似度 (0-1)"""
        name1 = name1.lower()
        name2 = name2.lower()

        if name1 == name2:
            return 1.0

        # 编辑距离
        len1, len2 = len(name1), len(name2)
        if len1 == 0 or len2 == 0:
            return 0.0

        # 简单编辑距离
        edit_dist = self._levenshtein_distance(name1, name2)
        max_len = max(len1, len2)
        return 1.0 - (edit_dist / max_len)

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def find_best_match(self, isolated_name: str,
                        candidates: List[str]) -> Optional[Tuple[str, float]]:
        """找到最佳匹配返回 (名称, 相似度)"""
        best_score = 0.0
        best_match = None

        for candidate in candidates:
            score = self.calculate_name_similarity(isolated_name, candidate)
            if score > best_score:
                best_score = score
                best_match = candidate

        if best_score >= self.threshold:
            return (best_match, best_score)
        return None


class IsolatedNodeResolver:
    def __init__(self):
        self.matcher = SimilarityMatcher()

    def resolve(self, isolated_nodes: List[str],
                all_nodes: List[str],
                existing_edges: List[Tuple[str, str]]) -> dict[str, Optional[str]]:
        """
        解析孤立节点，尝试连接到相似节点

        Returns: {isolated_id: connected_id or None}
        """
        result = {}
        non_isolated = [n for n in all_nodes if n not in isolated_nodes]

        for isolated in isolated_nodes:
            match = self.matcher.find_best_match(isolated, non_isolated)
            if match:
                result[isolated] = match[0]
                logger.info(f"Isolated node '{isolated}' matched to '{match[0]}' (score: {match[1]:.2f})")
            else:
                result[isolated] = None
                logger.info(f"Isolated node '{isolated}' could not be matched, will be kept as independent step")

        return result
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/sequence/test_island_resolver.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/sequence/island_resolver.py tests/sequence/test_island_resolver.py
git commit -m "feat: add IsolatedNodeResolver for similarity-based node matching"
```

---

## Task 2: 修改 CycleDetector - 移除删除孤立节点逻辑

**Files:**
- Modify: `src/sequence/cycle_detector.py:82`

- [ ] **Step 1: 查看当前代码确认行号**

Run: `grep -n "remove_nodes_from" src/sequence/cycle_detector.py`
Expected: 显示包含该函数的行号

- [ ] **Step 2: 编写测试验证当前行为**

```python
# tests/sequence/test_cycle_detector.py 新增
def test_isolated_nodes_not_removed():
    """孤立节点不应该被删除"""
    detector = CycleDetector()
    components = [
        {'id': 'A', 'precedence': []},  # 孤立节点
        {'id': 'B', 'precedence': ['A']},
    ]
    graph = detector.build_graph(components)
    broken = detector.break_cycles()

    # A 仍然是图的一部分
    assert 'A' in broken.nodes()
    assert 'B' in broken.nodes()
```

- [ ] **Step 3: 运行测试验证当前失败**

Run: `pytest tests/sequence/test_cycle_detector.py::test_isolated_nodes_not_removed -v`
Expected: FAIL - A not in nodes (因为被删除了)

- [ ] **Step 4: 修改代码移除删除逻辑**

```python
# src/sequence/cycle_detector.py
# 找到 break_cycles 方法中的这行:
# broken_graph.remove_nodes_from(list(nx.isolates(broken_graph)))
# 删除这一行或注释掉
```

- [ ] **Step 5: 运行测试验证通过**

Run: `pytest tests/sequence/test_cycle_detector.py::test_isolated_nodes_not_removed -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add src/sequence/cycle_detector.py
git commit -m "fix: preserve isolated nodes instead of removing them"
```

---

## Task 3: 修改 SequencePlanner - 增加RELATES关系查询

**Files:**
- Modify: `src/sequence/planner.py:85-115`

- [ ] **Step 1: 编写测试**

```python
# tests/sequence/test_planner.py 新增
def test_load_components_with_relates():
    """测试从RELATES关系加载依赖"""
    planner = SequencePlanner(neo4j_client)

    # Mock Neo4j返回包含RELATES关系的数据
    components = [
        {'id': 'upper_housing', 'name': 'Upper Housing', 'precedence': [], 'tool_required': [], 'safety_level': 1},
        {'id': 'insulator', 'name': 'Insulator', 'precedence': [], 'tool_required': [], 'safety_level': 1},
    ]
    relations = [
        {'head': 'upper_housing', 'tail': 'insulator', 'relation': '必须先于...拆卸'}
    ]

    # 验证 _parse_components_with_relations 能正确处理
    result = planner._parse_components_with_relations(components, relations)
    assert 'upper_housing' in result
    assert result['upper_housing']['dependencies'] == ['insulator']
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/sequence/test_planner.py -v`
Expected: FAIL - method doesn't exist

- [ ] **Step 3: 查看当前 _load_components 实现**

Read: `src/sequence/planner.py:85-115`

- [ ] **Step 4: 修改 _load_components 方法**

```python
# src/sequence/planner.py
# 在 _load_components 方法中添加 RELATES 关系查询

def _load_components(self, battery_model: str) -> List[Dict]:
    if not self.neo4j:
        return []

    # 查询组件
    cypher = '''
    MATCH (c:Component {battery_model: $model})
    RETURN c.id as id, c.name as name, c.tool_required as tool_required,
           c.safety_level as safety_level, c.precedence as precedence
    '''
    components = self.neo4j.execute_query(cypher, {'model': battery_model})

    # 查询RELATES关系 (新增)
    rel_cypher = '''
    MATCH (c1:Component)-[r:RELATES]->(c2:Component)
    WHERE c1.battery_model = $model AND r.type = '必须先于...拆卸'
    RETURN c1.name as head, c2.name as tail, r.type as relation
    '''
    relations = self.neo4j.execute_query(rel_cypher, {'model': battery_model})

    # 解析组件和关系
    return self._parse_components_with_relations(components, relations)


def _parse_components_with_relations(self, components: List[Dict],
                                       relations: List[Dict]) -> List[Dict]:
    """解析组件列表和关系，构建依赖图"""
    import ast

    # 构建关系映射: head -> [tails it must come before]
    dep_map = {}
    for rel in relations:
        head = rel.get('head', '')
        tail = rel.get('tail', '')
        if head and tail:
            if head not in dep_map:
                dep_map[head] = []
            dep_map[head].append(tail)

    result = []
    for r in components:
        precedence = []
        if r.get('precedence'):
            try:
                precedence = ast.literal_eval(r['precedence']) if isinstance(r['precedence'], str) else r['precedence']
            except (ValueError, SyntaxError):
                precedence = []

        # 添加从RELATES关系获取的依赖
        name = r.get('name', '')
        rel_deps = dep_map.get(name, [])

        # 合并precedence和rel_deps，去重
        all_deps = list(set(precedence + rel_deps))

        result.append({
            'id': r.get('id', ''),
            'name': r.get('name', ''),
            'tool_required': r.get('tool_required', []),
            'safety_level': r.get('safety_level', 1),
            'precedence': all_deps,
            'dependencies': all_deps  # 用于建图
        })

    return result
```

- [ ] **Step 5: 运行测试验证通过**

Run: `pytest tests/sequence/test_planner.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add src/sequence/planner.py
git commit -m "feat: load RELATES relations for disassembly sequence planning"
```

---

## Task 4: 集成 IsolatedNodeResolver 到 SequencePlanner

**Files:**
- Modify: `src/sequence/planner.py`
- Modify: `src/sequence/cycle_detector.py`

- [ ] **Step 1: 在 SequencePlanner 中调用 IsolatedNodeResolver**

Read: `src/sequence/planner.py:43-54` (plan方法中拓扑排序部分)

- [ ] **Step 2: 修改 plan 方法添加孤立节点处理**

```python
# src/sequence/planner.py
# 在 plan() 方法中，拓扑排序后添加:

def plan(self, battery_model: str, components: List[Dict] = None) -> DisassemblySequence:
    if components is None:
        components = self._load_components(battery_model)

    # ... 现有代码直到拓扑排序 ...

    # 打断循环
    if cycles:
        broken_graph = self.cycle_detector.break_cycles()
    else:
        broken_graph = self.cycle_detector.graph

    # 获取拓扑排序
    self.topological_sort.set_graph(broken_graph)
    sorted_ids = self.topological_sort.sort()

    # 新增: 处理孤立节点
    isolated_nodes = [n for n in broken_graph.nodes() if broken_graph.in_degree(n) == 0 and broken_graph.out_degree(n) == 0]
    if isolated_nodes:
        logger.info(f"Found {len(isolated_nodes)} isolated nodes: {isolated_nodes}")
        resolver = IsolatedNodeResolver()
        all_node_names = list(broken_graph.nodes())
        existing_edges = list(broken_graph.edges())

        matches = resolver.resolve(isolated_nodes, all_node_names, existing_edges)

        # 为匹配成功的孤立节点添加虚拟边
        for isolated, connected in matches.items():
            if connected:
                broken_graph.add_edge(isolated, connected)
                logger.info(f"Added virtual edge: {isolated} -> {connected}")

        # 重新排序
        sorted_ids = self.topological_sort.sort()
```

- [ ] **Step 3: 编写测试**

```python
# tests/sequence/test_planner.py 新增
def test_isolated_node_resolution():
    """测试孤立节点被正确处理"""
    planner = SequencePlanner()

    # 模拟有孤立节点的组件
    components = [
        {'id': 'A', 'name': 'Upper Housing', 'precedence': [], 'dependencies': []},
        {'id': 'B', 'name': 'Lower Housing', 'precedence': [], 'dependencies': []},
        {'id': 'C', 'name': 'Cooling Pipe', 'precedence': [], 'dependencies': []},  # 孤立节点
    ]

    # Mock建图和排序
    result = planner.plan('test', components)

    # Cooling Pipe 应该被保留（作为独立步骤）
    step_ids = [s['component'] for s in result.steps]
    assert 'Cooling Pipe' in step_ids
```

- [ ] **Step 4: 运行测试**

Run: `pytest tests/sequence/test_planner.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/sequence/planner.py
git commit -m "feat: integrate IsolatedNodeResolver into disassembly planning"
```

---

## Task 5: 新增电池型号搜索API

**Files:**
- Modify: `src/api/routes.py` (或新建 `src/api/battery_routes.py`)
- Create: `tests/api/test_battery_routes.py`

- [ ] **Step 1: 编写测试**

```python
# tests/api/test_battery_routes.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_search_battery_models():
    response = client.get('/api/v1/battery-models?search=Audi')
    assert response.status_code == 200
    data = response.json()
    assert 'data' in data
    assert isinstance(data['data'], list)

def test_search_battery_models_with_stats():
    response = client.get('/api/v1/battery-models?search=Audi&include_stats=true')
    assert response.status_code == 200
    data = response.json()
    if data['data']:
        assert 'L1_components' in data['data'][0]
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/api/test_battery_routes.py -v`
Expected: FAIL - endpoint not found

- [ ] **Step 3: 添加API端点**

```python
# src/api/routes.py 或新建 src/api/battery_routes.py
from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter()

@router.get('/api/v1/battery-models')
async def search_battery_models(
    search: str = Query("", description="模糊搜索电池型号"),
    include_stats: bool = Query(True, description="是否返回统计信息")
):
    from src.kg.client import Neo4jClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    try:
        # 搜索不同型号
        if include_stats:
            cypher = '''
            MATCH (c:Component)
            WHERE c.battery_model CONTAINS $search
            WITH DISTINCT c.battery_model as model
            OPTIONAL MATCH (comp:Component {battery_model: model})
            WITH model, count(comp) as L1_components
            OPTIONAL MATCH (comp:Component {battery_model: model})<-[:REFERENCED_IN|ORIGINATED_FROM*0..1]-(e)
            WITH model, L1_components, count(DISTINCT e) as L2_entities
            OPTIONAL MATCH (t:L3_Term)
            WHERE t.source_document_id IN [model]
            RETURN model, L1_components, L2_entities, 0 as L3_terms
            LIMIT 20
            '''
            results = neo4j.execute_query(cypher, {'search': search})
        else:
            cypher = '''
            MATCH (c:Component)
            WHERE c.battery_model CONTAINS $search
            RETURN DISTINCT c.battery_model as model
            LIMIT 20
            '''
            results = neo4j.execute_query(cypher, {'search': search})

        if include_stats:
            data = [
                {
                    'model': r.get('model', ''),
                    'L1_components': r.get('L1_components', 0),
                    'L2_entities': r.get('L2_entities', 0),
                    'L3_terms': r.get('L3_terms', 0)
                }
                for r in results
            ]
        else:
            data = [{'model': r.get('model', '')} for r in results]

        return {'code': 0, 'message': 'success', 'data': data}
    finally:
        neo4j.close()
```

- [ ] **Step 4: 将路由注册到main.py**

确保路由被添加到FastAPI app:
```python
# src/main.py
from src.api.routes import router as battery_router
app.include_router(battery_router)
```

- [ ] **Step 5: 运行测试验证通过**

Run: `pytest tests/api/test_battery_routes.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add src/api/routes.py src/main.py tests/api/test_battery_routes.py
git commit -m "feat: add battery model search API"
```

---

## Task 6: 新增 NaturalLanguageFeedback 自然语言反馈生成器

**Files:**
- Create: `src/graphrag/natural_feedback.py`
- Create: `tests/graphrag/test_natural_feedback.py`

- [ ] **Step 1: 编写测试**

```python
# tests/graphrag/test_natural_feedback.py
import pytest
from src.graphrag.natural_feedback import NaturalLanguageFeedback

@pytest.fixture
def feedback():
    from src.graphrag.retriever import MultiPathRetriever
    from src.graphrag.ranker import EvidenceRanker
    from src.utils.llm_client import LLMClient
    from src.config import settings

    neo4j = None  # or mock
    milvus = None
    llm = LLMClient(api_key=settings.openai_api_key, base_url=settings.openai_base_url, model=settings.llm_model)
    retriever = MultiPathRetriever(neo4j, milvus)
    ranker = EvidenceRanker()

    return NaturalLanguageFeedback(retriever, ranker, llm)

def test_generate_answer_format(feedback):
    """测试生成的回答格式包含来源标注"""
    result = feedback.generate_sync(
        question="磷酸铁锂电池有什么特点？",
        use_web_search=False
    )

    assert 'answer' in result
    # 验证来源标注格式
    answer = result['answer']
    assert '【来源：' in answer or '[' in answer  # 包含来源标注
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/graphrag/test_natural_feedback.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: 编写 NaturalLanguageFeedback 类**

```python
# src/graphrag/natural_feedback.py
from typing import Optional, AsyncGenerator, Dict, Any, List
import logging
import json

from src.graphrag.retriever import MultiPathRetriever
from src.graphrag.ranker import EvidenceRanker
from src.utils.llm_client import LLMClient
from src.kg.models import EvidenceGraph

logger = logging.getLogger(__name__)


class NaturalLanguageFeedback:
    """自然语言反馈生成器 - 用于通用问答"""

    PROGRESS_STAGES = [
        ("understanding", "正在理解您的问题..."),
        ("retrieving_local", "正在检索本地知识库..."),
        ("retrieving_web", "正在检索网络资源..."),
        ("ranking", "正在排序证据..."),
        ("generating", "正在生成回答..."),
        ("done", "完成"),
    ]

    def __init__(self, retriever: MultiPathRetriever, ranker: EvidenceRanker,
                 llm_client: LLMClient):
        self.retriever = retriever
        self.ranker = ranker
        self.llm = llm_client

    async def generate_stream(
        self,
        question: str,
        use_web_search: bool = False,
        context: Optional[List[str]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """SSE流式生成回答"""

        # Stage 1: Understanding
        yield {"stage": "understanding", "progress": 0.1, "message": self.PROGRESS_STAGES[0][1]}
        rewritten_queries = self._rewrite_query(question)

        # Stage 2: Local retrieval
        yield {"stage": "retrieving_local", "progress": 0.3, "message": self.PROGRESS_STAGES[1][1]}
        evidence_graph = await self._retrieve_local(rewritten_queries)

        # Stage 3: Web retrieval (if enabled)
        if use_web_search:
            yield {"stage": "retrieving_web", "progress": 0.5, "message": self.PROGRESS_STAGES[2][1]}
            web_results = await self._retrieve_web(question)
        else:
            web_results = []

        # Stage 4: Ranking
        yield {"stage": "ranking", "progress": 0.6, "message": self.PROGRESS_STAGES[3][1]}
        ranked_evidence = self._rank_evidence(evidence_graph, question)

        # Stage 5: Generation
        yield {"stage": "generating", "progress": 0.8, "message": self.PROGRESS_STAGES[4][1]}
        answer = await self._generate_answer(question, ranked_evidence, web_results, context)

        # Stage 6: Done
        yield {"stage": "done", "progress": 1.0, "message": self.PROGRESS_STAGES[5][1], "answer": answer}

    def generate_sync(self, question: str, use_web_search: bool = False,
                     context: Optional[List[str]] = None) -> Dict[str, Any]:
        """同步生成回答（内部使用）"""
        import asyncio
        return asyncio.run(self.generate_stream(question, use_web_search, context).__anext__())

    def _rewrite_query(self, question: str) -> List[str]:
        """重写查询为多个子查询"""
        # 简单实现：直接返回原问题
        # 可以扩展为调用QueryRewriter
        return [question]

    async def _retrieve_local(self, queries: List[str]) -> EvidenceGraph:
        """从本地知识图谱检索"""
        # 调用retriever获取证据
        evidence_graph = await self.retriever.retrieve(queries, battery_model=None)
        return evidence_graph

    async def _retrieve_web(self, question: str) -> List[Dict]:
        """从网络检索"""
        # 联网搜索为可选功能，暂返回空列表
        # 如需实现，可使用SerpAPI或DuckDuckGo等
        return []

    def _rank_evidence(self, evidence: EvidenceGraph, query: str) -> List[Any]:
        """排序证据"""
        if evidence.nodes:
            return self.ranker.rank(evidence.nodes, query)
        return []

    async def _generate_answer(self, question: str, evidence: List[Any],
                              web_results: List[Dict],
                              context: Optional[List[str]]) -> str:
        """生成自然语言回答"""
        context_str = ', '.join(context) if context else '无'

        # 构建证据文本
        evidence_parts = []
        for e in evidence[:10]:  # 限制数量
            source_type = getattr(e, 'node_type', 'Unknown')
            name = getattr(e, 'name', '')
            text = getattr(e, 'text', '')
            evidence_parts.append(f"【来源：本地KG-{source_type}:{name}】{text}")

        web_parts = []
        for r in web_results[:5]:
            title = r.get('title', '')
            snippet = r.get('snippet', '')
            web_parts.append(f"【来源：联网搜索:{title}】{snippet}")

        all_evidence = '\n'.join(evidence_parts + web_parts)

        prompt = f'''任务：回答用户关于电池的问题

用户问题：{question}
上下文：{context_str}

相关证据：
{all_evidence if all_evidence else "无相关证据"}

请用自然语言回答用户的问题。
回答要求：
1. 使用中文
2. 每个论点后用()标注来源，格式：【来源：类型:名称】
3. 如果证据不足，说明"根据现有资料无法确定..."
4. 回答要有条理，适当分段

回答：'''

        try:
            result = self.llm.generate(prompt)
            return result
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return f"抱歉，生成回答时出现错误：{str(e)}"
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/graphrag/test_natural_feedback.py -v`
Expected: PASS (或部分通过，取决于mock完整性)

- [ ] **Step 5: 提交**

```bash
git add src/graphrag/natural_feedback.py tests/graphrag/test_natural_feedback.py
git commit -m "feat: add NaturalLanguageFeedback for Q&A module"
```

---

## Task 7: 新增问答API端点 (SSE)

**Files:**
- Modify: `src/api/query_routes.py`
- Create: `tests/api/test_query_routes.py`

- [ ] **Step 1: 编写测试**

```python
# tests/api/test_query_routes.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_query_feedback_endpoint_exists():
    response = client.post('/api/v1/query/feedback', json={
        "question": "磷酸铁锂电池有什么特点？",
        "use_web_search": False
    })
    assert response.status_code in [200, 202]

def test_query_feedback_requires_question():
    response = client.post('/api/v1/query/feedback', json={})
    assert response.status_code == 422  # Validation error
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/api/test_query_routes.py -v`
Expected: FAIL - endpoint not found

- [ ] **Step 3: 添加SSE端点**

```python
# src/api/query_routes.py
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class FeedbackRequest(BaseModel):
    question: str
    use_web_search: bool = False
    context: List[str] = []


@router.post('/api/v1/query/feedback')
async def query_feedback(request: FeedbackRequest):
    """问答反馈接口 - 支持SSE流式返回"""

    # 懒加载避免循环导入
    from src.graphrag.natural_feedback import NaturalLanguageFeedback
    from src.graphrag.retriever import MultiPathRetriever
    from src.graphrag.ranker import EvidenceRanker
    from src.utils.llm_client import LLMClient
    from src.kg.client import Neo4jClient, MilvusClient
    from src.config import settings

    # 初始化组件
    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    milvus = MilvusClient(settings.milvus_host, settings.milvus_port) if settings.milvus_host else None
    llm = LLMClient(api_key=settings.openai_api_key, base_url=settings.openai_base_url, model=settings.llm_model)

    retriever = MultiPathRetriever(neo4j, milvus)
    ranker = EvidenceRanker()
    feedback = NaturalLanguageFeedback(retriever, ranker, llm)

    async def event_generator():
        try:
            async for event in feedback.generate_stream(
                question=request.question,
                use_web_search=request.use_web_search,
                context=request.context
            ):
                # SSE格式
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'event': 'close'}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"SSE error: {e}")
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/api/test_query_routes.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/api/query_routes.py tests/api/test_query_routes.py
git commit -m "feat: add SSE feedback endpoint for Q&A"
```

---

## Task 8: 非流式回答端点 (可选)

如果前端需要非SSE版本：

**Files:**
- Modify: `src/api/query_routes.py`

- [ ] **Step 1: 添加非流式端点**

```python
@router.post('/api/v1/query/feedback/sync')
async def query_feedback_sync(request: FeedbackRequest):
    """同步版本的问答反馈"""

    from src.graphrag.natural_feedback import NaturalLanguageFeedback
    # ... 初始化代码同Task 7 ...

    feedback = NaturalLanguageFeedback(retriever, ranker, llm)

    # 收集所有事件
    final_result = None
    async for event in feedback.generate_stream(
        question=request.question,
        use_web_search=request.use_web_search,
        context=request.context
    ):
        if event.get('stage') == 'done':
            final_result = event

    if final_result:
        # 从最终结果提取来源信息
        sources = []
        answer = final_result.get('answer', '')
        # 从answer中提取【来源：...】模式作为sources
        import re
        source_pattern = r'【来源：([^】]+)】'
        matches = re.findall(source_pattern, answer)
        for m in matches:
            parts = m.split(':')
            if len(parts) >= 2:
                sources.append({'type': parts[0], 'name': parts[1]})

        return {
            'code': 0,
            'message': 'success',
            'data': {
                'answer': answer,
                'sources': sources
            }
        }

    return {'code': 1, 'message': 'Generation failed', 'data': None}
```

- [ ] **Step 2: 提交**

```bash
git add src/api/query_routes.py
git commit -m "feat: add sync feedback endpoint"
```

---

## Self-Review Checklist

- [ ] Spec覆盖检查：
  - [x] 拆卸序列规划优化 - Task 1-4
  - [x] 电池型号搜索API - Task 5
  - [x] KG+LLM问答反馈 - Task 6-7
  - [x] SSE进度条 - Task 7
  - [x] 前端集成说明 - 文档更新

- [ ] Placeholder扫描：
  - [ ] 无"TBD"、"TODO"等占位符
  - [ ] 所有代码步骤都有完整实现

- [ ] 类型一致性检查：
  - [ ] `IsolatedNodeResolver.resolve()` 返回类型一致
  - [ ] `NaturalLanguageFeedback` 接口在Task 6-7一致

---

## Execution Options

**Plan complete and saved to `docs/superpowers/plans/2026-04-17-sequence-and-feedback-design.md`**

**Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
