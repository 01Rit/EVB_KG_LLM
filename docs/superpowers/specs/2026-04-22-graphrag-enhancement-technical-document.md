# GraphRAG增强功能技术文档

**日期**: 2026-04-22
**版本**: 1.0
**状态**: 已完成设计

---

## 文档目的

本文档提供GraphRAG系统三项增强功能的完整技术说明，包括架构设计、数据模型、接口定义、实现细节和测试策略。

---

## 目录

1. [系统概述](#1-系统概述)
2. [功能1：KG-aware RAG（结构约束感知的检索）](#2-功能1kg-aware-rag结构约束感知的检索)
3. [功能2：可解释推理输出（Explainable Reasoning）](#3-功能2可解释推理输出explainable-reasoning)
4. [功能3：再制造路径推荐（Remanufacturing Routing）](#4-功能3再制造路径推荐remanufacturing-routing)
5. [实施顺序与依赖关系](#5-实施顺序与依赖关系)
6. [测试策略](#6-测试策略)

---

## 1. 系统概述

### 1.1 现有GraphRAG架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Planner                                      │
│  ┌──────────┐   ┌──────────────┐   ┌──────┐   ┌──────────┐          │
│  │  Query   │──▶│  Retriever  │──▶│Ranker│──▶│Generator │          │
│  │ Rewriter │   │(MultiPath)  │   │      │   │          │          │
│  └──────────┘   └──────────────┘   └──────┘   └──────────┘          │
│       │                                                   │          │
│       │              ┌──────────┐                        │          │
│       └─────────────▶│ Feedback │◀───────────────────────┘          │
│                      │  Loop    │                                     │
│                      └──────────┘                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 增强后的架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Planner                                        │
│  ┌──────────┐   ┌──────────────────────┐   ┌──────┐   ┌──────────┐    │
│  │  Query   │──▶│ ConstraintAware      │──▶│Ranker│──▶│Generator │    │
│  │ Rewriter │   │ Retriever (NEW)      │   │      │   │          │    │
│  └──────────┘   │ ┌────────────────┐  │   └──────┘   └──────────┘    │
│       │         │ │ConstraintEngine│  │        │           │          │
│       │         │ │   (NEW)        │  │        │           │          │
│       │         │ └────────────────┘  │        │           │          │
│       │         └──────────────────────┘        │           │          │
│       │                                            │    ┌──────────┐    │
│       │              ┌──────────┐                 │    │Evidence  │    │
│       └─────────────▶│ Feedback │◀────────────────┘    │Tracer    │    │
│                      │  Loop    │                      │(NEW)     │    │
│                      └──────────┘                      └──────────┘    │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │              RemanufacturingScorer (NEW)                         │   │
│  │   输出: discard | recycle | remanufacture | repair | reuse       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 功能1：KG-aware RAG（结构约束感知的检索）

### 2.1 核心概念

**问题**: 传统RAG仅基于语义相似性检索，可能返回违反物理约束的组件序列。

**解决方案**: 在检索阶段引入结构约束，只返回满足BEFORE/AFTER关系的有效拆卸序列。

### 2.2 约束推导规则

#### 规则1：外层优先规则

```python
OUTER_KEYWORDS = ['housing', 'cover', 'shell', 'case', 'cap']
INNER_KEYWORDS = ['cell', 'module', 'cmc', 'electrode']

# 如果组件A名称包含outer关键词，组件B名称包含inner关键词
# 则推断: A BEFORE B
```

#### 规则2：安全级别规则

```python
# 如果 safety_level(A) > safety_level(B)
# 则推断: A BEFORE B (高安全级别先拆)
```

#### 规则3：工具互斥规则（未来扩展）

```python
# 如果两个组件使用相同的工具
# 则它们可以并行拆卸
```

### 2.3 ConstraintEngine 接口

```python
# src/graphrag/constraint_engine.py

class ConstraintEngine:
    def __init__(self, neo4j_client=None):
        self._neo4j = neo4j_client
        self.OUTER_KEYWORDS = ['housing', 'cover', 'shell', 'case', 'cap']
        self.INNER_KEYWORDS = ['cell', 'module', 'cmc', 'electrode']

    def infer_bidirectional_constraints(
        self,
        battery_model: str,
        components: list[dict]
    ) -> list[dict]:
        """
        推导组件间的BEFORE/AFTER双向约束

        Args:
            battery_model: 电池型号
            components: 组件列表，每个包含 name, safety_level 等

        Returns:
            约束列表: [{'head': 'A', 'relation': 'BEFORE', 'tail': 'B'}, ...]
        """
```

### 2.4 ConstraintAwareRetriever 实现

```python
# src/graphrag/constrained_retriever.py

class ConstraintAwareRetriever(MultiPathRetriever):
    async def retrieve(
        self,
        intents: list[str],
        battery_model: str,
        top_k: int = 30
    ) -> EvidenceGraph:
        # 1. 语义检索（继承父类行为）
        semantic_results = await super().retrieve(intents, battery_model, top_k)

        # 2. 提取组件信息用于约束推导
        components = [
            {
                'name': n.name,
                'safety_level': n.properties.get('safety_level', 3),
                'id': n.id
            }
            for n in semantic_results.nodes
        ]

        # 3. 推导约束边
        constraints = self.constraint_engine.infer_bidirectional_constraints(
            battery_model, components
        )

        # 4. 筛选满足约束的子图
        valid_subgraph = self._filter_valid_subgraph(semantic_results, constraints)

        return valid_subgraph
```

### 2.5 约束过滤算法

```python
def _filter_valid_subgraph(self, evidence: EvidenceGraph, constraints: list[dict]) -> EvidenceGraph:
    """
    过滤逻辑：
    1. 构建约束图（有向边表示BEFORE关系）
    2. 对节点进行拓扑排序
    3. 检查当前节点序列是否满足约束
    4. 如不满足，返回拓扑排序后的有效子图
    """
```

### 2.6 Planner 集成

```python
# src/graphrag/planner.py

class Planner:
    def __init__(self, llm_client, retriever, neo4j_client=None,
                 use_constraint_retriever: bool = False):
        # ... 现有初始化 ...

        if use_constraint_retriever and neo4j_client:
            from src.graphrag.constraint_engine import ConstraintEngine
            from src.graphrag.constrained_retriever import ConstraintAwareRetriever
            constraint_engine = ConstraintEngine(neo4j_client)
            self.retriever = ConstraintAwareRetriever(
                neo4j_client, None, constraint_engine
            )
```

---

## 3. 功能2：可解释推理输出（Explainable Reasoning）

### 3.1 核心概念

**问题**: 用户无法理解"为什么选择先拆A而不是B"。

**解决方案**: 为每个拆卸步骤提供结构化的证据来源引用，支持追溯具体KG节点。

### 3.2 数据模型扩展

#### EvidenceNode 扩展

```python
# src/kg/models.py

class EvidenceNode(BaseModel):
    node_type: str
    id: str
    name: str
    properties: dict[str, Any]
    relationships: list[str] = []
    text: str
    evidence_ids: list[str] = []  # 新增：关联的证据节点ID列表
```

#### Step Schema 扩展

```python
# src/api/schemas.py

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
    # ... 其他现有字段 ...
```

### 3.3 EvidenceTracer 实现

```python
# src/graphrag/evidence_tracer.py

class EvidenceTracer:
    def trace_step(self, step: dict, evidence_graph: EvidenceGraph) -> dict:
        """
        为单个步骤追溯其使用的证据节点

        Args:
            step: 拆卸步骤，包含 component 字段
            evidence_graph: 检索得到的证据图

        Returns:
            包含 evidence_sources 的步骤字典
        """
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
        """批量追溯所有步骤的证据"""
        for step in steps:
            trace_result = self.trace_step(step, evidence_graph)
            step['evidence_sources'] = trace_result['evidence_sources']
        return steps

    def _node_to_source(self, node: EvidenceNode) -> dict:
        return {
            'node_id': node.id,
            'node_type': node.node_type,
            'name': node.name,
            'text': node.text,
            'properties': node.properties
        }
```

### 3.4 Generator Prompt 修改

```python
# src/graphrag/generator.py

PLAN_GENERATION_PROMPT = '''...
请以JSON格式返回，包含steps数组，每个元素包含:
- id, component, action, tool, safety_level, depends_on
- confidence: float - 本步骤的置信度 (0-1)
- evidence_ids: list[str] - 本步骤使用的证据节点ID列表

【重要】请从检索结果中选择与本步骤最相关的节点ID，填入 evidence_ids'''
```

### 3.5 Planner 集成

```python
# src/graphrag/planner.py - _plan_local 方法

async def _plan_local(self, query, battery_model, context, debug):
    # ... 检索逻辑 ...

    initial_plan = self.generator.generate(query, evidence_graph, battery_model, context, kg_context)

    # 新增：证据追溯
    from src.graphrag.evidence_tracer import EvidenceTracer
    tracer = EvidenceTracer()
    if initial_plan.get('steps'):
        initial_plan['steps'] = tracer.trace_all_steps(
            initial_plan['steps'], evidence_graph
        )

    # ... 后续处理 ...
```

---

## 4. 功能3：再制造路径推荐（Remanufacturing Routing）

### 4.1 核心概念

**问题**: 拆卸后的组件如何处理？manual决策效率低。

**解决方案**: 基于多目标评分，为每个拆卸步骤推荐最优处理路径。

### 4.2 路径优先级定义

```
路径优先级（从低到高）:
1. discard      - 直接报废
2. recycle      - 材料回收
3. remanufacture- 再制造
4. repair       - 维修翻新
5. reuse        - 直接再利用
```

### 4.3 多目标评分模型

#### 评分因素

| 因素 | 权重 | 说明 |
|------|------|------|
| 组件状态 | 30% | 基于 safety_level，越高状态越好 |
| 经济价值 | 40% | 基于组件元数据 value_score |
| 环境影响 | 30% | 基于 carbon_footprint，越低越好 |

#### 路径权重配置

```python
PATHWAY_WEIGHTS = {
    'discard':        {'state': 0.1, 'value': 0.1, 'env': 0.8},   # 环境最敏感
    'recycle':        {'state': 0.2, 'value': 0.3, 'env': 0.5},
    'remanufacture':  {'state': 0.4, 'value': 0.4, 'env': 0.2},
    'repair':         {'state': 0.6, 'value': 0.2, 'env': 0.2},
    'reuse':          {'state': 0.8, 'value': 0.1, 'env': 0.1},   # 状态最敏感
}
```

#### 评分函数

```python
# src/graphrag/remanufacturing_scorer.py

class RemanufacturingScorer:
    def score_pathway(self, component: dict, battery_model: str) -> dict:
        """
        计算最优再制造路径

        Args:
            component: 组件属性，包含 safety_level, value_score, carbon_footprint
            battery_model: 电池型号

        Returns:
            {
                'recommended': 'repair',      # 推荐路径
                'confidence': 0.85,           # 置信度
                'scores': {                   # 各路径评分
                    'discard': 0.1,
                    'recycle': 0.3,
                    'remanufacture': 0.6,
                    'repair': 0.85,
                    'reuse': 0.7
                }
            }
        """
        state_score = self._calc_state_score(component)      # 0-1
        value_score = self._calc_value_score(component)    # 0-1
        env_score = self._calc_environment_score(component) # 0-1

        final_scores = {}
        for pathway in PATHWAY_ORDER:
            w = PATHWAY_WEIGHTS[pathway]
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
```

### 4.4 Planner 集成

```python
# src/graphrag/planner.py

def _enrich_steps_with_remanufacturing(self, steps: list, battery_model: str) -> list:
    from src.graphrag.remanufacturing_scorer import RemanufacturingScorer
    scorer = RemanufacturingScorer()
    return scorer.score_all_steps(steps, battery_model)
```

在 `_plan_local` 中调用：

```python
steps = self._enrich_steps_with_scores(steps, battery_model)
steps = self._enrich_steps_with_remanufacturing(steps, battery_model)  # 新增
```

---

## 5. 实施顺序与依赖关系

### 5.1 推荐的实施顺序

```
Phase 1 ──────────────────────────────▶ Phase 2 ──────────────────────────────▶ Phase 3
┌─────────────────────────────┐        ┌─────────────────────────────┐        ┌─────────────────────────────┐
│ Explainable Reasoning       │        │ KG-aware RAG                │        │ Remanufacturing Routing     │
│ (可解释推理输出)             │        │ (结构约束感知检索)           │        │ (再制造路径推荐)            │
├─────────────────────────────┤        ├─────────────────────────────┤        ├─────────────────────────────┤
│ • 风险最低                  │        │ • 需要约束推导算法验证       │        │ • 可复用Phase 1的基础设施   │
│ • 立即可见效                │        │ • 与Phase 1部分并行         │        │ • 独立模块                   │
│ • 独立于其他Phase           │        │                              │        │                              │
└─────────────────────────────┘        └─────────────────────────────┘        └─────────────────────────────┘
```

### 5.2 文件变更清单

| Phase | 文件 | 操作 | 职责 |
|-------|------|------|------|
| 1 | `src/kg/models.py` | 修改 | 添加 evidence_ids 到 EvidenceNode |
| 1 | `src/graphrag/evidence_tracer.py` | 新增 | 证据追溯服务 |
| 1 | `src/graphrag/generator.py` | 修改 | Prompt 增加 evidence_ids |
| 1 | `src/graphrag/planner.py` | 修改 | 集成 EvidenceTracer |
| 1 | `src/api/schemas.py` | 修改 | 添加 EvidenceSource, evidence_sources |
| 2 | `src/graphrag/constraint_engine.py` | 新增 | 约束推导引擎 |
| 2 | `src/graphrag/constrained_retriever.py` | 新增 | 约束感知检索器 |
| 2 | `src/graphrag/planner.py` | 修改 | 支持 ConstraintAwareRetriever |
| 3 | `src/graphrag/remanufacturing_scorer.py` | 新增 | 再制造评分器 |
| 3 | `src/api/schemas.py` | 修改 | 添加 remanufacturing_pathway 字段 |
| 3 | `src/graphrag/planner.py` | 修改 | 集成 RemanufacturingScorer |

---

## 6. 测试策略

### 6.1 单元测试

#### EvidenceTracer 测试

```python
# tests/graphrag/test_evidence_tracer.py

def test_trace_step_finds_matching_node():
    tracer = EvidenceTracer()
    evidence_graph = EvidenceGraph(nodes=[
        EvidenceNode(node_type='Component', id='c1', name='housing',
                     properties={}, relationships=[], text='Housing')
    ], edges=[])
    step = {'id': 1, 'component': 'housing'}

    result = tracer.trace_step(step, evidence_graph)

    assert result['evidence_sources'][0]['name'] == 'housing'
```

#### ConstraintEngine 测试

```python
# tests/graphrag/test_constraint_engine.py

def test_housing_before_cell():
    engine = ConstraintEngine()
    components = [
        {'name': 'upper_housing', 'safety_level': 1},
        {'name': 'cell', 'safety_level': 4}
    ]
    constraints = engine.infer_bidirectional_constraints('battery', components)
    before_pairs = [(c['head'], c['tail']) for c in constraints if c['relation'] == 'BEFORE']

    assert ('upper_housing', 'cell') in before_pairs
```

#### RemanufacturingScorer 测试

```python
# tests/graphrag/test_remanufacturing_scorer.py

def test_high_safety_low_value_recycle():
    scorer = RemanufacturingScorer()
    component = {'safety_level': 1, 'value_score': 0.2, 'carbon_footprint': 0.8}

    result = scorer.score_pathway(component, 'battery')

    assert result['scores']['recycle'] > result['scores']['reuse']
```

### 6.2 集成测试

```python
# tests/graphrag/test_enhanced_planner_integration.py

@pytest.mark.asyncio
async def test_planner_returns_steps_with_evidence_sources():
    """验证完整流程返回包含 evidence_sources 的步骤"""
    pass

@pytest.mark.asyncio
async def test_planner_returns_steps_with_remanufacturing_pathway():
    """验证完整流程返回包含 remanufacturing_pathway 的步骤"""
    pass
```

### 6.3 评估指标

| 功能 | 指标 | 测试方法 |
|------|------|---------|
| Explainable Reasoning | evidence_sources 覆盖率 | 端到端测试检查所有步骤 |
| KG-aware RAG | 序列满足约束比例 | 约束验证测试 |
| Remanufacturing Routing | 评分合理性 | 专家评审 |

---

## 附录A：API响应示例

### 拆卸规划响应（含三项增强功能）

```json
{
  "code": 0,
  "message": "Success",
  "data": {
    "steps": [
      {
        "id": 1,
        "component": "upper_housing",
        "action": "Remove screws and lift cover",
        "tool": ["screwdriver", "pry_tool"],
        "safety_level": 1,
        "depends_on": [],
        "confidence": 0.95,
        "evidence_sources": [
          {
            "node_id": "comp_001",
            "node_type": "Component",
            "name": "upper_housing",
            "text": "Upper housing component"
          }
        ],
        "remanufacturing_pathway": "reuse",
        "pathway_confidence": 0.82,
        "pathway_scores": {
          "discard": 0.1,
          "recycle": 0.3,
          "remanufacture": 0.5,
          "repair": 0.7,
          "reuse": 0.82
        }
      }
    ],
    "parallel_batches": [...],
    "total_time_seconds": 3600
  }
}
```

---

## 附录B：配置参数

```yaml
# config.yaml

graphrag:
  # KG-aware RAG
  constraint_inference:
    enabled: true
    outer_keywords: ['housing', 'cover', 'shell', 'case', 'cap']
    inner_keywords: ['cell', 'module', 'cmc', 'electrode']

  # Explainable Reasoning
  evidence_tracer:
    enabled: true
    max_sources_per_step: 10

  # Remanufacturing Routing
  remanufacturing:
    enabled: true
    pathway_weights:
      discard:        {state: 0.1, value: 0.1, env: 0.8}
      recycle:        {state: 0.2, value: 0.3, env: 0.5}
      remanufacture:  {state: 0.4, value: 0.4, env: 0.2}
      repair:         {state: 0.6, value: 0.2, env: 0.2}
      reuse:          {state: 0.8, value: 0.1, env: 0.1}
```
