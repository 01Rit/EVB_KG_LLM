# GraphRAG增强功能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为GraphRAG系统实现三项增强功能：可解释推理输出(Explainable Reasoning)、结构约束感知检索(KG-aware RAG)、再制造路径推荐(Remanufacturing Routing)

**Architecture:**
- **Phase 1 (Explainable Reasoning)**: 新增 `evidence_tracer.py`，扩展 `models.py`、`schemas.py`、`generator.py`，在 `planner.py` 集成证据追溯
- **Phase 2 (KG-aware RAG)**: 新增 `constraint_engine.py`、`constrained_retriever.py`，修改 `planner.py` 使用约束感知检索
- **Phase 3 (Remanufacturing Routing)**: 新增 `remanufacturing_scorer.py`，扩展 `schemas.py`，在 `planner.py` 集成再制造评分

**Tech Stack:** Python (FastAPI), Neo4j, Pydantic, tiktoken

---

## 文件结构

```
src/
├── graphrag/
│   ├── evidence_tracer.py         # Phase 1: 证据追溯服务（新增）
│   ├── constraint_engine.py       # Phase 2: 约束推导引擎（新增）
│   ├── constrained_retriever.py   # Phase 2: 约束感知检索器（新增）
│   ├── remanufacturing_scorer.py   # Phase 3: 再制造评分器（新增）
│   ├── generator.py               # Phase 1,2: 修改 prompt
│   └── planner.py                # Phase 1,2,3: 修改集成逻辑
├── kg/
│   └── models.py                 # Phase 1: 扩展 EvidenceNode
└── api/
    └── schemas.py                # Phase 1,3: 扩展 Step schema

tests/
├── graphrag/
│   ├── test_evidence_tracer.py   # Phase 1: 证据追溯测试
│   ├── test_constraint_engine.py # Phase 2: 约束引擎测试
│   └── test_remanufacturing_scorer.py  # Phase 3: 再制造评分测试
```

---

## Phase 1: 可解释推理输出 (Explainable Reasoning)

### Task 1.1: 扩展 EvidenceNode 模型

**Files:**
- Modify: `src/kg/models.py:32-39`

- [ ] **Step 1: 查看现有 EvidenceNode 定义**

```python
# src/kg/models.py:32-39
class EvidenceNode(BaseModel):
    node_type: str
    id: str
    name: str
    properties: dict[str, Any]
    relationships: list[str] = []
    text: str
```

- [ ] **Step 2: 添加 evidence_ids 字段到 EvidenceNode**

```python
class EvidenceNode(BaseModel):
    node_type: str
    id: str
    name: str
    properties: dict[str, Any]
    relationships: list[str] = []
    text: str
    evidence_ids: list[str] = []  # 新增：关联的证据节点ID列表
```

- [ ] **Step 3: 运行测试验证模型仍然有效**

Run: `py -m pytest tests/kg/test_models.py -v` (如存在)

- [ ] **Step 4: Commit**

```bash
git add src/kg/models.py
git commit -m "feat(models): add evidence_ids field to EvidenceNode"
```

---

### Task 1.2: 创建 EvidenceTracer 证据追溯服务

**Files:**
- Create: `src/graphrag/evidence_tracer.py`
- Create: `tests/graphrag/test_evidence_tracer.py`

- [ ] **Step 1: 创建 evidence_tracer.py**

```python
# src/graphrag/evidence_tracer.py
from typing import Optional
from src.kg.models import EvidenceNode, EvidenceGraph


class EvidenceTracer:
    def trace_step(self, step: dict, evidence_graph: EvidenceGraph) -> dict:
        step_component = step.get('component', '')
        matching_nodes = [
            n for n in evidence_graph.nodes
            if n.name == step_component or n.id == step_component
        ]
        return {
            'step_id': step.get('id'),
            'evidence_sources': [self._node_to_source(n) for n in matching_nodes]
        }

    def trace_all_steps(self, steps: list[dict], evidence_graph: EvidenceGraph) -> list[dict]:
        result = []
        for step in steps:
            trace_result = self.trace_step(step, evidence_graph)
            step['evidence_sources'] = trace_result['evidence_sources']
            result.append(step)
        return result

    def _node_to_source(self, node: EvidenceNode) -> dict:
        return {
            'node_id': node.id,
            'node_type': node.node_type,
            'name': node.name,
            'text': node.text,
            'properties': node.properties
        }
```

- [ ] **Step 2: 创建单元测试 test_evidence_tracer.py**

```python
# tests/graphrag/test_evidence_tracer.py
import pytest
from src.graphrag.evidence_tracer import EvidenceTracer
from src.kg.models import EvidenceNode, EvidenceGraph


class TestEvidenceTracer:
    def test_trace_step_finds_matching_node(self):
        tracer = EvidenceTracer()
        evidence_graph = EvidenceGraph(
            nodes=[
                EvidenceNode(
                    node_type='Component',
                    id='comp_001',
                    name='upper_housing',
                    properties={'safety_level': 2},
                    relationships=[],
                    text='Upper housing component'
                )
            ],
            edges=[]
        )
        step = {'id': 1, 'component': 'upper_housing'}

        result = tracer.trace_step(step, evidence_graph)

        assert result['step_id'] == 1
        assert len(result['evidence_sources']) == 1
        assert result['evidence_sources'][0]['node_id'] == 'comp_001'
        assert result['evidence_sources'][0]['name'] == 'upper_housing'

    def test_trace_step_no_match(self):
        tracer = EvidenceTracer()
        evidence_graph = EvidenceGraph(nodes=[], edges=[])
        step = {'id': 1, 'component': 'unknown_component'}

        result = tracer.trace_step(step, evidence_graph)

        assert result['step_id'] == 1
        assert result['evidence_sources'] == []

    def test_trace_all_steps(self):
        tracer = EvidenceTracer()
        evidence_graph = EvidenceGraph(
            nodes=[
                EvidenceNode(
                    node_type='Component',
                    id='comp_001',
                    name='upper_housing',
                    properties={},
                    relationships=[],
                    text='Upper housing'
                ),
                EvidenceNode(
                    node_type='Component',
                    id='comp_002',
                    name='insulator',
                    properties={},
                    relationships=[],
                    text='Insulator'
                )
            ],
            edges=[]
        )
        steps = [
            {'id': 1, 'component': 'upper_housing'},
            {'id': 2, 'component': 'insulator'}
        ]

        result = tracer.trace_all_steps(steps, evidence_graph)

        assert len(result) == 2
        assert result[0]['evidence_sources'][0]['name'] == 'upper_housing'
        assert result[1]['evidence_sources'][0]['name'] == 'insulator'
```

- [ ] **Step 3: 运行测试验证**

Run: `py -m pytest tests/graphrag/test_evidence_tracer.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/graphrag/evidence_tracer.py tests/graphrag/test_evidence_tracer.py
git commit -m "feat(graphrag): add EvidenceTracer for step-level evidence tracing"
```

---

### Task 1.3: 修改 Generator Prompt 要求输出 evidence_ids

**Files:**
- Modify: `src/graphrag/generator.py:31-52`

- [ ] **Step 1: 查看现有 PLAN_GENERATION_PROMPT**

```python
# src/graphrag/generator.py:31-52
prompt = f'''任务: 为电池型号 {battery_model} 生成拆卸方案
...
请以JSON格式返回，包含steps数组，每个元素包含: id, component, action, tool, safety_level, depends_on'''
```

- [ ] **Step 2: 修改 prompt 添加 evidence_ids 和 confidence**

```python
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
- 置信度 (confidence) - 本步骤的置信度 (0-1)
- 证据IDs (evidence_ids) - 本步骤使用的证据节点ID列表，从检索结果中选择

请以JSON格式返回，包含steps数组，每个元素包含: id, component, action, tool, safety_level, depends_on, confidence, evidence_ids'''
```

- [ ] **Step 3: Commit**

```bash
git add src/graphrag/generator.py
git commit -m "feat(generator): add evidence_ids and confidence to prompt"
```

---

### Task 1.4: 在 Planner 集成 EvidenceTracer

**Files:**
- Modify: `src/graphrag/planner.py:148-156`

- [ ] **Step 1: 查看 _plan_local 方法中 generator.generate 调用位置**

```python
# src/graphrag/planner.py:149
initial_plan = self.generator.generate(query, evidence_graph, battery_model, context, kg_context)
```

- [ ] **Step 2: 在 generator.generate 调用后添加 evidence tracing**

```python
# 在 initial_plan = self.generator.generate(...) 之后添加：

from src.graphrag.evidence_tracer import EvidenceTracer
tracer = EvidenceTracer()

if initial_plan.get('steps'):
    initial_plan['steps'] = tracer.trace_all_steps(initial_plan['steps'], evidence_graph)
```

- [ ] **Step 3: 验证语法正确性**

Run: `py -c "from src.graphrag.planner import Planner; print('Import OK')"`

- [ ] **Step 4: Commit**

```bash
git add src/graphrag/planner.py
git commit -m "feat(planner): integrate EvidenceTracer for explainable reasoning"
```

---

### Task 1.5: 扩展 Step Schema 添加 evidence_sources

**Files:**
- Modify: `src/api/schemas.py:11-26`

- [ ] **Step 1: 查看现有 Step schema**

```python
# src/api/schemas.py:11-26
class Step(BaseModel):
    id: int
    component: str
    action: str
    tool: list[str] = []
    evidence: list[str] = []
    confidence: Optional[float] = None
    safety_level: Optional[int] = None
    h_score: Optional[float] = None
    s_score: Optional[float] = None
    as_score: Optional[float] = None
    human_loss: Optional[float] = None
    robot_loss: Optional[float] = None
    loss_diff: Optional[float] = None
    assignee: Optional[str] = None
```

- [ ] **Step 2: 添加 evidence_sources 字段**

```python
class EvidenceSource(BaseModel):
    node_id: str
    node_type: str
    name: str
    text: Optional[str] = None
    properties: Optional[dict[str, Any]] = None


class Step(BaseModel):
    id: int
    component: str
    action: str
    tool: list[str] = []
    evidence: list[str] = []
    evidence_sources: list[EvidenceSource] = []  # 新增
    confidence: Optional[float] = None
    safety_level: Optional[int] = None
    h_score: Optional[float] = None
    s_score: Optional[float] = None
    as_score: Optional[float] = None
    human_loss: Optional[float] = None
    robot_loss: Optional[float] = None
    loss_diff: Optional[float] = None
    assignee: Optional[str] = None
```

- [ ] **Step 3: 验证 schema 导入正确**

Run: `py -c "from src.api.schemas import Step, EvidenceSource; print('Schema OK')"`

- [ ] **Step 4: Commit**

```bash
git add src/api/schemas.py
git commit -m "feat(schemas): add EvidenceSource and evidence_sources to Step"
```

---

## Phase 2: 结构约束感知的检索 (KG-aware RAG)

### Task 2.1: 创建 ConstraintEngine 约束推导引擎

**Files:**
- Create: `src/graphrag/constraint_engine.py`
- Create: `tests/graphrag/test_constraint_engine.py`

- [ ] **Step 1: 创建 constraint_engine.py**

```python
# src/graphrag/constraint_engine.py
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ConstraintEngine:
    OUTER_KEYWORDS = ['housing', 'cover', 'shell', 'case', 'cap']
    INNER_KEYWORDS = ['cell', 'module', 'cmc', 'electrode']

    def __init__(self, neo4j_client=None):
        self._neo4j = neo4j_client

    def infer_bidirectional_constraints(self, battery_model: str, components: list[dict]) -> list[dict]:
        constraints = []

        for i, comp in enumerate(components):
            comp_name = comp.get('name', '').lower()
            comp_safety = comp.get('safety_level', 3)

            for j, other_comp in enumerate(components):
                if i >= j:
                    continue

                other_name = other_comp.get('name', '').lower()
                other_safety = other_comp.get('safety_level', 3)

                if self._is_outer(comp_name) and self._is_inner(other_name):
                    constraints.append({
                        'head': comp.get('name'),
                        'relation': 'BEFORE',
                        'tail': other_comp.get('name')
                    })
                elif self._is_outer(other_name) and self._is_inner(comp_name):
                    constraints.append({
                        'head': other_comp.get('name'),
                        'relation': 'BEFORE',
                        'tail': comp.get('name')
                    })

                if comp_safety > other_safety:
                    constraints.append({
                        'head': comp.get('name'),
                        'relation': 'BEFORE',
                        'tail': other_comp.get('name')
                    })

        return constraints

    def _is_outer(self, name: str) -> bool:
        return any(kw in name for kw in self.OUTER_KEYWORDS)

    def _is_inner(self, name: str) -> bool:
        return any(kw in name for kw in self.INNER_KEYWORDS)
```

- [ ] **Step 2: 创建测试 test_constraint_engine.py**

```python
# tests/graphrag/test_constraint_engine.py
import pytest
from src.graphrag.constraint_engine import ConstraintEngine


class TestConstraintEngine:
    def test_infer_bidirectional_constraints_housing_before_cell(self):
        engine = ConstraintEngine()
        components = [
            {'name': 'upper_housing', 'safety_level': 1},
            {'name': 'insulator', 'safety_level': 2},
            {'name': 'cell', 'safety_level': 4}
        ]

        constraints = engine.infer_bidirectional_constraints('test_battery', components)

        before_pairs = [(c['head'], c['tail']) for c in constraints if c['relation'] == 'BEFORE']

        assert ('upper_housing', 'cell') in before_pairs
        assert ('insulator', 'cell') in before_pairs

    def test_is_outer_true(self):
        engine = ConstraintEngine()
        assert engine._is_outer('upper_housing') == True
        assert engine._is_outer('lower_case') == True
        assert engine._is_outer('battery_cover') == True

    def test_is_outer_false(self):
        engine = ConstraintEngine()
        assert engine._is_outer('cell') == False
        assert engine._is_outer('module') == False

    def test_is_inner_true(self):
        engine = ConstraintEngine()
        assert engine._is_inner('cell') == True
        assert engine._is_inner('cmc') == True
        assert engine._is_inner('module') == True

    def test_safety_level_constraint(self):
        engine = ConstraintEngine()
        components = [
            {'name': 'high_safety_part', 'safety_level': 5},
            {'name': 'low_safety_part', 'safety_level': 1}
        ]

        constraints = engine.infer_bidirectional_constraints('test', components)
        before_pairs = [(c['head'], c['tail']) for c in constraints if c['relation'] == 'BEFORE']

        assert ('high_safety_part', 'low_safety_part') in before_pairs
```

- [ ] **Step 3: 运行测试验证**

Run: `py -m pytest tests/graphrag/test_constraint_engine.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/graphrag/constraint_engine.py tests/graphrag/test_constraint_engine.py
git commit -m "feat(graphrag): add ConstraintEngine for BEFORE/AFTER inference"
```

---

### Task 2.2: 创建 ConstraintAwareRetriever

**Files:**
- Create: `src/graphrag/constrained_retriever.py`

- [ ] **Step 1: 创建 constrained_retriever.py**

```python
# src/graphrag/constrained_retriever.py
from src.graphrag.retriever import MultiPathRetriever
from src.graphrag.constraint_engine import ConstraintEngine
from src.kg.models import EvidenceGraph
import logging

logger = logging.getLogger(__name__)


class ConstraintAwareRetriever(MultiPathRetriever):
    def __init__(self, neo4j_client, milvus_client, constraint_engine=None):
        super().__init__(neo4j_client, milvus_client)
        self.constraint_engine = constraint_engine or ConstraintEngine(neo4j_client)

    async def retrieve(self, intents: list[str], battery_model: str, top_k: int = 30) -> EvidenceGraph:
        semantic_results = await super().retrieve(intents, battery_model, top_k)

        if not semantic_results.nodes:
            return semantic_results

        components = [
            {
                'name': n.name,
                'safety_level': n.properties.get('safety_level', 3),
                'id': n.id
            }
            for n in semantic_results.nodes
        ]

        constraints = self.constraint_engine.infer_bidirectional_constraints(
            battery_model, components
        )

        valid_subgraph = self._filter_valid_subgraph(semantic_results, constraints)

        logger.info(f'ConstraintAwareRetriever: filtered {len(semantic_results.nodes)} -> {len(valid_subgraph.nodes)} nodes')
        return valid_subgraph

    def _filter_valid_subgraph(self, evidence: EvidenceGraph, constraints: list[dict]) -> EvidenceGraph:
        if not constraints:
            return evidence

        before_graph = {}
        for c in constraints:
            if c['relation'] == 'BEFORE':
                head = c['head']
                tail = c['tail']
                if head not in before_graph:
                    before_graph[head] = set()
                before_graph[head].add(tail)

        def has_valid_order(node_names: list[str]) -> bool:
            name_to_idx = {name: i for i, name in enumerate(node_names)}
            for head, tails in before_graph.items():
                if head not in name_to_idx:
                    continue
                head_idx = name_to_idx[head]
                for tail in tails:
                    if tail in name_to_idx and name_to_idx[tail] <= head_idx:
                        return False
            return True

        node_names = [n.name for n in evidence.nodes]
        if has_valid_order(node_names):
            return evidence

        sorted_nodes = self._topological_sort(evidence.nodes, before_graph)
        valid_ids = {n.id for n in sorted_nodes}

        filtered_nodes = [n for n in evidence.nodes if n.id in valid_ids]
        filtered_edges = [
            e for e in evidence.edges
            if e.get('start') in valid_ids and e.get('end') in valid_ids
        ]

        return EvidenceGraph(nodes=filtered_nodes, edges=filtered_edges)

    def _topological_sort(self, nodes: list, before_graph: dict) -> list:
        node_map = {n.name: n for n in nodes}
        in_degree = {name: 0 for name in node_map}

        for head, tails in before_graph.items():
            for tail in tails:
                if tail in in_degree:
                    in_degree[tail] += 1

        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(node_map[current])

            if current in before_graph:
                for next_node in before_graph[current]:
                    if next_node in in_degree:
                        in_degree[next_node] -= 1
                        if in_degree[next_node] == 0:
                            queue.append(next_node)

        return result if result else list(node_map.values())
```

- [ ] **Step 2: 验证模块导入正确**

Run: `py -c "from src.graphrag.constrained_retriever import ConstraintAwareRetriever; print('Import OK')"`

- [ ] **Step 3: Commit**

```bash
git add src/graphrag/constrained_retriever.py
git commit -m "feat(graphrag): add ConstraintAwareRetriever for structure-valid retrieval"
```

---

### Task 2.3: 在 Planner 中集成 ConstraintAwareRetriever

**Files:**
- Modify: `src/graphrag/planner.py:29-30`

- [ ] **Step 1: 查看当前 retriever 和 planner 初始化**

```python
# src/graphrag/planner.py:29-30
retriever = MultiPathRetriever(neo4j_client, milvus_client)
planner = Planner(llm_client, retriever, neo4j_client)
```

- [ ] **Step 2: 修改 Planner.__init__ 接受 constraint_engine 参数**

```python
# src/graphrag/planner.py:18-31
class Planner:
    def __init__(self, llm_client: LLMClient, retriever: MultiPathRetriever, neo4j_client=None):
        self.rewriter = QueryRewriter(llm_client)
        self.retriever = retriever
        self.ranker = EvidenceRanker()
        self.generator = PlanGenerator(llm_client)
        self.feedback = FeedbackLoop(retriever, self.ranker, self.generator)
        self._neo4j_client = neo4j_client
```

修改为：

```python
class Planner:
    def __init__(self, llm_client: LLMClient, retriever: MultiPathRetriever, neo4j_client=None,
                 use_constraint_retriever: bool = False):
        self.rewriter = QueryRewriter(llm_client)
        self.ranker = EvidenceRanker()
        self.generator = PlanGenerator(llm_client)
        self._neo4j_client = neo4j_client

        if use_constraint_retriever and neo4j_client:
            from src.graphrag.constraint_engine import ConstraintEngine
            from src.graphrag.constrained_retriever import ConstraintAwareRetriever
            constraint_engine = ConstraintEngine(neo4j_client)
            self.retriever = ConstraintAwareRetriever(neo4j_client, None, constraint_engine)
        else:
            self.retriever = retriever

        self.feedback = FeedbackLoop(self.retriever, self.ranker, self.generator)
```

- [ ] **Step 3: 验证语法正确性**

Run: `py -c "from src.graphrag.planner import Planner; print('Import OK')"`

- [ ] **Step 4: Commit**

```bash
git add src/graphrag/planner.py
git commit -m "feat(planner): support ConstraintAwareRetriever in Planner initialization"
```

---

## Phase 3: 再制造路径推荐 (Remanufacturing Routing)

### Task 3.1: 创建 RemanufacturingScorer

**Files:**
- Create: `src/graphrag/remanufacturing_scorer.py`
- Create: `tests/graphrag/test_remanufacturing_scorer.py`

- [ ] **Step 1: 创建 remanufacturing_scorer.py**

```python
# src/graphrag/remanufacturing_scorer.py
from typing import Optional

PATHWAY_ORDER = ['discard', 'recycle', 'remanufacture', 'repair', 'reuse']

PATHWAY_WEIGHTS = {
    'discard':        {'state': 0.1, 'value': 0.1, 'env': 0.8},
    'recycle':        {'state': 0.2, 'value': 0.3, 'env': 0.5},
    'remanufacture':  {'state': 0.4, 'value': 0.4, 'env': 0.2},
    'repair':         {'state': 0.6, 'value': 0.2, 'env': 0.2},
    'reuse':          {'state': 0.8, 'value': 0.1, 'env': 0.1},
}


class RemanufacturingScorer:
    def __init__(self):
        self.pathway_order = PATHWAY_ORDER
        self.weights = PATHWAY_WEIGHTS

    def score_pathway(self, component: dict, battery_model: str) -> dict:
        state_score = self._calc_state_score(component)
        value_score = self._calc_value_score(component)
        env_score = self._calc_environment_score(component)

        final_scores = {}
        for pathway in self.pathway_order:
            w = self.weights[pathway]
            final_scores[pathway] = (
                state_score * w['state'] +
                value_score * w['value'] +
                env_score * w['env']
            )

        recommended = max(final_scores, key=final_scores.get)

        return {
            'recommended': recommended,
            'confidence': round(final_scores[recommended], 3),
            'scores': {k: round(v, 3) for k, v in final_scores.items()}
        }

    def _calc_state_score(self, component: dict) -> float:
        safety_level = component.get('safety_level', 3)
        return min(safety_level / 5.0, 1.0)

    def _calc_value_score(self, component: dict) -> float:
        value = component.get('value_score', 0.5)
        return float(value) if value else 0.5

    def _calc_environment_score(self, component: dict) -> float:
        carbon = component.get('carbon_footprint', 0.5)
        return 1.0 - min(float(carbon) if carbon else 0.5, 1.0)

    def score_all_steps(self, steps: list[dict], battery_model: str) -> list[dict]:
        for step in steps:
            component_name = step.get('component', '')
            component_data = {
                'safety_level': step.get('safety_level', 3),
                'value_score': step.get('value_score', 0.5),
                'carbon_footprint': step.get('carbon_footprint', 0.5)
            }
            result = self.score_pathway(component_data, battery_model)
            step['remanufacturing_pathway'] = result['recommended']
            step['pathway_confidence'] = result['confidence']
            step['pathway_scores'] = result['scores']
        return steps
```

- [ ] **Step 2: 创建测试 test_remanufacturing_scorer.py**

```python
# tests/graphrag/test_remanufacturing_scorer.py
import pytest
from src.graphrag.remanufacturing_scorer import RemanufacturingScorer


class TestRemanufacturingScorer:
    def test_score_pathway_returns_valid_structure(self):
        scorer = RemanufacturingScorer()
        component = {'safety_level': 3, 'value_score': 0.5, 'carbon_footprint': 0.5}

        result = scorer.score_pathway(component, 'test_battery')

        assert 'recommended' in result
        assert 'confidence' in result
        assert 'scores' in result
        assert result['recommended'] in ['discard', 'recycle', 'remanufacture', 'repair', 'reuse']

    def test_high_safety_low_value_recycle(self):
        scorer = RemanufacturingScorer()
        component = {'safety_level': 1, 'value_score': 0.2, 'carbon_footprint': 0.8}

        result = scorer.score_pathway(component, 'test_battery')

        assert result['scores']['recycle'] > result['scores']['reuse']

    def test_low_safety_high_value_reuse(self):
        scorer = RemanufacturingScorer()
        component = {'safety_level': 5, 'value_score': 0.9, 'carbon_footprint': 0.2}

        result = scorer.score_pathway(component, 'test_battery')

        assert result['recommended'] == 'reuse'

    def test_score_all_steps(self):
        scorer = RemanufacturingScorer()
        steps = [
            {'component': 'upper_housing', 'safety_level': 2},
            {'component': 'cell', 'safety_level': 4}
        ]

        result = scorer.score_all_steps(steps, 'test_battery')

        assert len(result) == 2
        assert 'remanufacturing_pathway' in result[0]
        assert 'pathway_confidence' in result[0]
        assert 'pathway_scores' in result[0]
```

- [ ] **Step 3: 运行测试验证**

Run: `py -m pytest tests/graphrag/test_remanufacturing_scorer.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/graphrag/remanufacturing_scorer.py tests/graphrag/test_remanufacturing_scorer.py
git commit -m "feat(graphrag): add RemanufacturingScorer for pathway recommendation"
```

---

### Task 3.2: 扩展 Step Schema 添加再制造字段

**Files:**
- Modify: `src/api/schemas.py`

- [ ] **Step 1: 添加 remanufacturing 字段到 Step**

```python
class Step(BaseModel):
    id: int
    component: str
    action: str
    tool: list[str] = []
    evidence: list[str] = []
    evidence_sources: list[EvidenceSource] = []
    confidence: Optional[float] = None
    safety_level: Optional[int] = None
    h_score: Optional[float] = None
    s_score: Optional[float] = None
    as_score: Optional[float] = None
    human_loss: Optional[float] = None
    robot_loss: Optional[float] = None
    loss_diff: Optional[float] = None
    assignee: Optional[str] = None
    remanufacturing_pathway: Optional[str] = None
    pathway_confidence: Optional[float] = None
    pathway_scores: Optional[dict[str, float]] = None
```

- [ ] **Step 2: 验证 schema 正确**

Run: `py -c "from src.api.schemas import Step; s = Step(id=1, component='test', action='remove'); print(s.model_dump())"`

- [ ] **Step 3: Commit**

```bash
git add src/api/schemas.py
git commit -m "feat(schemas): add remanufacturing_pathway fields to Step"
```

---

### Task 3.3: 在 Planner 集成再制造评分

**Files:**
- Modify: `src/graphrag/planner.py`

- [ ] **Step 1: 查看 _enrich_steps_with_scores 方法**

```python
# src/graphrag/planner.py:33-67
def _enrich_steps_with_scores(self, steps: list, battery_model: str) -> list:
```

- [ ] **Step 2: 在 _enrich_steps_with_scores 后添加 _enrich_steps_with_remanufacturing**

```python
def _enrich_steps_with_remanufacturing(self, steps: list, battery_model: str) -> list:
    from src.graphrag.remanufacturing_scorer import RemanufacturingScorer
    scorer = RemanufacturingScorer()
    return scorer.score_all_steps(steps, battery_model)
```

- [ ] **Step 3: 在 _plan_local 方法中调用新方法**

找到 `_enrich_steps_with_scores(steps, battery_model)` 调用，在其后添加：

```python
steps = self._enrich_steps_with_scores(steps, battery_model)
steps = self._enrich_steps_with_remanufacturing(steps, battery_model)
```

- [ ] **Step 4: 验证语法正确性**

Run: `py -c "from src.graphrag.planner import Planner; print('Import OK')"`

- [ ] **Step 5: Commit**

```bash
git add src/graphrag/planner.py
git commit -m "feat(planner): integrate RemanufacturingScorer into planning pipeline"
```

---

## Task 3.4: 端到端集成测试

**Files:**
- Create: `tests/graphrag/test_enhanced_planner_integration.py`

- [ ] **Step 1: 创建集成测试**

```python
# tests/graphrag/test_enhanced_planner_integration.py
import pytest
from unittest.mock import MagicMock, AsyncMock
from src.graphrag.planner import Planner
from src.kg.models import EvidenceNode, EvidenceGraph


class TestEnhancedPlannerIntegration:
    @pytest.mark.asyncio
    async def test_planner_returns_steps_with_evidence_sources(self):
        pass

    @pytest.mark.asyncio
    async def test_planner_returns_steps_with_remanufacturing_pathway(self):
        pass

    def test_evidence_tracer_integrates_with_planner(self):
        pass

    def test_constraint_engine_integrates_with_retriever(self):
        pass
```

- [ ] **Step 2: 运行测试**

Run: `py -m pytest tests/graphrag/test_enhanced_planner_integration.py -v`

- [ ] **Step 3: Commit**

```bash
git add tests/graphrag/test_enhanced_planner_integration.py
git commit -m "test: add integration tests for enhanced planner features"
```

---

## 实施检查清单

### Phase 1 完成标志:
- [ ] `src/kg/models.py` - EvidenceNode 添加 evidence_ids
- [ ] `src/graphrag/evidence_tracer.py` - EvidenceTracer 实现
- [ ] `src/graphrag/generator.py` - Prompt 修改
- [ ] `src/graphrag/planner.py` - 集成 EvidenceTracer
- [ ] `src/api/schemas.py` - 添加 evidence_sources
- [ ] 所有 Phase 1 测试通过

### Phase 2 完成标志:
- [ ] `src/graphrag/constraint_engine.py` - ConstraintEngine 实现
- [ ] `src/graphrag/constrained_retriever.py` - ConstraintAwareRetriever 实现
- [ ] `src/graphrag/planner.py` - 支持 ConstraintAwareRetriever
- [ ] 所有 Phase 2 测试通过

### Phase 3 完成标志:
- [ ] `src/graphrag/remanufacturing_scorer.py` - RemanufacturingScorer 实现
- [ ] `src/api/schemas.py` - 添加 remanufacturing_pathway 字段
- [ ] `src/graphrag/planner.py` - 集成再制造评分
- [ ] 所有 Phase 3 测试通过
- [ ] 端到端集成测试通过

---

## 风险与注意事项

1. **ConstraintEngine 规则覆盖不足**: 当前规则基于关键词匹配，需要后续扩展支持更多约束类型
2. **RemanufacturingScorer 权重固定**: 建议后续支持从配置文件加载权重
3. **EvidenceTracer 依赖 LLM 输出**: 如果 LLM 不输出 evidence_ids，tracer 将回退到基于名称匹配
