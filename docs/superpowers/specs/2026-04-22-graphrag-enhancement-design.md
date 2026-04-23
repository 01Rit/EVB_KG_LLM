# GraphRAG增强功能设计文档

**日期**: 2026-04-22
**版本**: 1.0
**状态**: Draft

---

## 概述

本文档描述对现有GraphRAG系统的三项功能增强：

1. **KG-aware RAG（结构约束感知的检索）** - 检索结果满足物理约束
2. **Explainable Reasoning（可解释推理输出）** - 拆卸步骤可追溯证据来源
3. **Remanufacturing Routing（再制造路径推荐）** - 拆卸规划附带最优处理路径

---

## 功能1：KG-aware RAG（结构约束感知的检索）

### 1.1 目标

将检索范式从"语义相似性优先"转变为"结构有效性优先"。检索结果必须是满足BEFORE/AFTER约束的有效拆卸序列子图，而非仅与查询语义相关的节点集合。

### 1.2 约束类型与推导规则

#### 约束边类型
新增以下边类型到Neo4j：
- `BEFORE`: 必须在某组件之前拆卸
- `AFTER`: 必须在某组件之后拆卸
- `REQUIRES_TOOL_MUTEX`: 与某组件使用相同工具，互斥

#### 自动推导规则

| 规则 | 条件 | 推断结果 |
|------|------|---------|
| 外层优先 | 组件名称含 housing/cover/shell | BEFORE 更深层组件 |
| 安全级别 | safety_level 高 → 低 | 高安全级别 BEFORE 低安全级别 |
| 工具互斥 | tool_required 包含 battery_holder | 与使用不同工具的组件可并行 |
| 关键词顺序 | 出现 insulator/cell/module | insulator BEFORE cell, cell BEFORE module |

### 1.3 架构设计

```
src/graphrag/
├── constraint_engine.py        # 约束推导引擎（新增）
├── constrained_retriever.py     # 约束感知检索器（新增）
└── planner.py                   # 修改：使用ConstrainedRetriever
```

#### ConstraintEngine

```python
class ConstraintEngine:
    def infer_bidirectional_constraints(self, battery_model: str) -> list[dict]:
        """
        推导组件间的BEFORE/AFTER双向约束
        Returns: [{head: "upper_housing", relation: "BEFORE", tail: "insulator"}, ...]
        """
```

#### ConstraintAwareRetriever

```python
class ConstraintAwareRetriever(MultiPathRetriever):
    def __init__(self, neo4j_client, milvus_client, constraint_engine):
        super().__init__(neo4j_client, milvus_client)
        self.constraint_engine = constraint_engine

    async def retrieve(self, intents: list[str], battery_model: str, top_k: int = 30) -> EvidenceGraph:
        # 1. 获取语义检索结果
        semantic_results = await super().retrieve(intents, battery_model, top_k)

        # 2. 推导约束边
        constraints = self.constraint_engine.infer_bidirectional_constraints(battery_model)

        # 3. 筛选满足约束的子图
        valid_subgraph = self._filter_valid_subgraph(semantic_results, constraints)

        return valid_subgraph
```

### 1.4 数据流

```
Query → ConstraintEngine.infer_constraints()
      → MultiPathRetriever.semantic_retrieve()
      → _filter_valid_subgraph(约束检查)
      → Valid EvidenceGraph
```

### 1.5 约束检查算法

```python
def _filter_valid_subgraph(self, evidence: EvidenceGraph, constraints: list[dict]) -> EvidenceGraph:
    """
    过滤逻辑：
    1. 构建约束图（有向边表示BEFORE关系）
    2. 对节点进行拓扑排序
    3. 返回满足所有BEFORE/AFTER约束的最大子图
    """
    # 伪代码参考 sequence/topological_sort.py
```

### 1.6 影响评估

| 指标 | 当前 | 预期 |
|------|------|------|
| 序列有效性 | ~70% | ~90%+ |
| 反馈迭代次数 | 3次 | 1-2次 |
| 检索延迟 | 基准 | +15% |

---

## 功能2：可解释推理输出（Explainable Reasoning）

### 2.1 目标

为每个拆卸步骤提供结构化的证据来源引用，支持前端追溯查看具体KG节点详情。

### 2.2 数据模型扩展

#### EvidenceNode 扩展（src/kg/models.py）

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

#### Step Schema 扩展（src/api/schemas.py）

```python
class Step(BaseModel):
    id: int
    component: str
    action: str
    tool: list[str] = []
    evidence: list[str] = []       # 新增：证据节点ID列表
    evidence_sources: list[dict] = []  # 新增：证据详情 [{node_id, node_type, name}]
    confidence: Optional[float] = None
    # ... 现有字段
```

### 2.3 架构设计

```
src/graphrag/
├── evidence_tracer.py      # 证据追溯服务（新增）
├── generator.py            # 修改：要求LLM输出evidence_ids
└── planner.py              # 修改：调用EvidenceTracer
```

#### EvidenceTracer

```python
class EvidenceTracer:
    def trace_step(self, step: dict, evidence_graph: EvidenceGraph) -> dict:
        """
        为单个步骤追溯其使用的证据节点
        返回: {step_id, evidence_sources: [{node_id, node_type, name, text}]}
        """
        step_component = step.get('component', '')
        # 在evidence_graph中查找匹配的节点
        matching_nodes = [n for n in evidence_graph.nodes if n.name == step_component]
        return {
            'step_id': step['id'],
            'evidence_sources': [self._node_to_source(n) for n in matching_nodes]
        }

    def _node_to_source(self, node: EvidenceNode) -> dict:
        return {
            'node_id': node.id,
            'node_type': node.node_type,
            'name': node.name,
            'text': node.text,
            'properties': node.properties
        }
```

### 2.4 Generator Prompt 修改

```python
PLAN_GENERATION_PROMPT = '''...
请以JSON格式返回，包含steps数组，每个元素包含:
- id, component, action, tool, safety_level, depends_on
- evidence_ids: list[str] - 本步骤使用的证据节点ID列表（从检索结果中选择）
- confidence: float - 本步骤的置信度 (0-1)
'''
```

### 2.5 Planner 集成

```python
# src/graphrag/planner.py

async def _plan_local(self, query, battery_model, context, debug):
    # ... 现有检索逻辑 ...

    # 生成初始规划
    initial_plan = self.generator.generate(query, evidence_graph, battery_model, context, kg_context)

    # 新增：证据追溯
    tracer = EvidenceTracer()
    for step in initial_plan.get('steps', []):
        trace_result = tracer.trace_step(step, evidence_graph)
        step['evidence_sources'] = trace_result['evidence_sources']

    # ... 后续反馈循环 ...
```

### 2.6 前端展示

```typescript
// 前端类型定义
interface Step {
  id: number;
  component: string;
  action: string;
  evidence_sources: Array<{
    node_id: string;
    node_type: string;
    name: string;
    text: string;
  }>;
  // ...
}

// 点击查看证据详情
onEvidenceClick(nodeId: string) {
  // 调用 /api/v1/graph/node/{nodeId} 获取节点详情
}
```

### 2.7 影响评估

| 指标 | 当前 | 预期 |
|------|------|------|
| 证据可追溯性 | 无 | 100% |
| 用户信任度 | - | +30% |
| Prompt token | 基准 | +10% |

---

## 功能3：再制造路径推荐（Remanufacturing Routing）

### 3.1 目标

作为拆卸规划的副产物，为每个拆卸步骤推荐最优的再制造处理路径（discard → recycle → remanufacture → repair → reuse）。

### 3.2 路径优先级定义

```
路径优先级（从低到高）:
1. discard      - 直接报废
2. recycle      - 材料回收
3. remanufacture- 再制造
4. repair       - 维修翻新
5. reuse        - 直接再利用
```

### 3.3 多目标评分模型

#### 评分因素

| 因素 | 权重 | 数据来源 |
|------|------|---------|
| 组件状态 | 30% | safety_level + 损伤检测 |
| 经济价值 | 40% | 组件元数据 value_score |
| 环境影响 | 30% | carbon_footprint |

#### 评分函数

```python
class RemanufacturingScorer:
    PATHWAY_ORDER = ['discard', 'recycle', 'remanufacture', 'repair', 'reuse']

    def score_pathway(self, component: dict, battery_model: str) -> dict:
        """
        返回: {
            'recommended': 'repair',
            'confidence': 0.85,
            'scores': {
                'discard': 0.1,
                'recycle': 0.3,
                'remanufacture': 0.6,
                'repair': 0.85,
                'reuse': 0.7
            }
        }
        """
        state_score = self._calc_state_score(component)      # 30%
        value_score = self._calc_value_score(component)        # 40%
        env_score = self._calc_environment_score(component)     # 30%

        final_scores = {}
        for pathway in self.PATHWAY_ORDER:
            # 各路径对不同因素的敏感度不同
            final_scores[pathway] = (
                state_score * PATHWAY_WEIGHTS[pathway]['state'] +
                value_score * PATHWAY_WEIGHTS[pathway]['value'] +
                env_score * PATHWAY_WEIGHTS[pathway]['env']
            )

        recommended = max(final_scores, key=final_scores.get)
        return {
            'recommended': recommended,
            'confidence': final_scores[recommended],
            'scores': final_scores
        }
```

#### 路径权重配置

```python
PATHWAY_WEIGHTS = {
    'discard':        {'state': 0.1, 'value': 0.1, 'env': 0.8},
    'recycle':        {'state': 0.2, 'value': 0.3, 'env': 0.5},
    'remanufacture':  {'state': 0.4, 'value': 0.4, 'env': 0.2},
    'repair':         {'state': 0.6, 'value': 0.2, 'env': 0.2},
    'reuse':          {'state': 0.8, 'value': 0.1, 'env': 0.1},
}
```

### 3.4 架构设计

```
src/graphrag/
├── remanufacturing_scorer.py   # 再制造评分器（新增）
└── planner.py                  # 修改：_enrich_steps_with_remanufacturing

src/api/
└── schemas.py                  # 修改：Step 增加 remanufacturing_pathway 等字段
```

### 3.5 Schema 扩展

```python
class Step(BaseModel):
    # ... 现有字段 ...
    remanufacturing_pathway: Optional[str] = None    # 新增
    pathway_confidence: Optional[float] = None       # 新增
    pathway_scores: Optional[dict[str, float]] = None # 新增
```

### 3.6 Planner 集成

```python
# src/graphrag/planner.py

def _enrich_steps_with_remanufacturing(self, steps: list, battery_model: str) -> list:
    scorer = RemanufacturingScorer()
    for step in steps:
        component = step.get('component', '')
        # 获取组件完整属性
        component_data = self._neo4j.get_component_by_name(component)
        if component_data:
            result = scorer.score_pathway(component_data, battery_model)
            step['remanufacturing_pathway'] = result['recommended']
            step['pathway_confidence'] = result['confidence']
            step['pathway_scores'] = result['scores']
    return steps
```

### 3.7 Planner 流程修改

```python
async def _plan_local(self, query, battery_model, context, debug):
    # ... 生成 steps ...

    # 现有：_enrich_steps_with_scores
    steps = self._enrich_steps_with_scores(steps, battery_model)

    # 新增：_enrich_steps_with_remanufacturing
    steps = self._enrich_steps_with_remanufacturing(steps, battery_model)

    # ... 时间估算、并行调度 ...
```

### 3.8 影响评估

| 指标 | 当前 | 预期 |
|------|------|------|
| 方案商业价值 | - | 可量化 |
| 再制造决策支持 | 手动 | 自动 |
| 环境影响评估 | 无 | 量化 |

---

## 实施顺序建议

1. **Phase 1**: 可解释推理输出（风险最低，立即可见效）
2. **Phase 2**: KG-aware RAG（需要约束推导算法验证）
3. **Phase 3**: 再制造路径推荐（依赖Phase 1的基础设施）

---

## 依赖关系

```
Feature 1 (KG-aware RAG)
├── 需要: constraint_engine.py
├── 修改: constrained_retriever.py
└── 影响: planner.py

Feature 2 (Explainable Reasoning)
├── 需要: evidence_tracer.py
├── 修改: models.py, schemas.py, generator.py, planner.py
└── 独立于 Feature 1

Feature 3 (Remanufacturing Routing)
├── 需要: remanufacturing_scorer.py
├── 修改: schemas.py, planner.py
└── 可基于 Feature 2 的 trace 结果
```

---

## 测试策略

1. **Feature 1**: 验证约束推导正确性 + 序列有效性
2. **Feature 2**: 单元测试 tracer，集成测试端到端追溯
3. **Feature 3**: 评分函数单元测试 + 专家评审评分合理性

---

## 风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| 约束推导规则不完整 | 提供人工标注界面持续优化 |
| 证据追溯准确率低 | 使用强类型schema + LLM self-check |
| 再制造评分主观性强 | 配置化权重，支持专家调参 |
