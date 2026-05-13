# LLM 推理反馈增强设计

**日期**: 2026-05-13
**项目**: 电池拆卸知识图谱推理反馈系统
**方案**: B — 中等重构，引入 ReasoningTrace

---

## 1. 背景与目标

### 现状问题

| 问题 | 根因 |
|------|------|
| 多跳跨层缺失 | `FeedbackLoop` 仅调用 `_retrieve_components()` 拉取 L1 节点，`CrossLayerRetriever` 仅在初始检索时触发，反馈迭代中未触发 |
| 推理链不透明 | LLM 自评 confidence(0-1) 无 chain-of-thought，`EvidenceTracer` 是事后追溯非内置推理 |
| 联网搜索未实现 | `NaturalLanguageFeedback._retrieve_web()` 返回 `[]` |

### 目标

1. 反馈迭代中支持 L1→L2→L3 全链路跨层检索
2. 推理链作为一等公民暴露在 API response 和前端
3. DuckDuckGo 联网搜索与本地知识并行融合

---

## 2. 架构设计

### 核心新增：`ReasoningTrace`

新增 `src/graphrag/reasoning_trace.py`，贯穿全流程：

```python
class ReasoningTrace:
    query: str                          # 当前推理 query
    iteration: int                      # 第几轮迭代
    retrieved_nodes: List[Node]         # 本轮检索到的节点
    cross_layer_expansion: Dict[str, Any] # 跨层扩展记录
        # {
        #   "l1_nodes": [...],
        #   "l2_nodes": [...],
        #   "l3_nodes": [...],
        #   "paths": [("L1_id", "REFERENCE_OF", "L2_id"), ...]
        # }
    confidence_factors: Dict[str, float]  # 置信度因子
        # {
        #   "evidence_coverage": 0.0-1.0,  # 步骤中覆盖的证据节点比例
        #   "cross_layer_depth": 0.0-1.0,  # 跨层深度得分 (0/0.33/0.67/1.0)
        #   "consistency": 0.0-1.0,        # 与前序步骤的一致性
        # }
    confidence: float                   # 综合置信度
    reasoning_steps: List[str]           # 推理步骤描述（用于展示）
    web_results: List[Dict]              # 联网搜索结果
    missing_evidence: List[str]          # 本轮发现的缺失证据
```

### 置信度公式

```
confidence = 0.5 * evidence_coverage + 0.3 * cross_layer_depth + 0.2 * consistency
```

- **evidence_coverage**: plan 中有 evidence 支撑的步骤 / 总步骤数
- **cross_layer_depth**: 每步按触及的最高层归一化计分（L1=0.33, L2=0.67, L3=1.0），取所有步骤平均
- **consistency**: 步骤间依赖关系与 evidence 图谱的一致性（LLM 评估）

---

## 3. 模块改动

### 3.1 FeedbackLoop 重构

**文件**: `src/graphrag/feedback.py`

```python
class FeedbackLoop:
    async def refine(self, query, initial_plan, evidence, battery_model, context) -> tuple[dict, EvidenceGraph, List[ReasoningTrace]]:
        traces = []
        for iteration in range(self.max_iterations):
            trace = ReasoningTrace(query=query, iteration=iteration)

            # 1. 跨层检索（每次迭代都触发）
            cross_layer_nodes = await self._retrieve_cross_layer(missing_evidence, trace)
            evidence.expand(cross_layer_nodes)

            # 2. 置信度因子计算
            trace.confidence_factors = self._calc_confidence_factors(evidence, initial_plan)
            trace.confidence = self._compute_confidence(trace.confidence_factors)

            # 3. 推理步骤记录
            trace.reasoning_steps.append(f"迭代 {iteration+1}: 检索到 {len(cross_layer_nodes)} 个节点，置信度 {trace.confidence:.2f}")

            # 4. 检查是否继续
            missing_evidence = self._extract_missing_evidence(initial_plan, evidence)
            trace.missing_evidence = missing_evidence
            if not missing_evidence:
                break

            initial_plan = self.generator.regenerate(...)

        return initial_plan, evidence, traces
```

### 3.2 跨层检索新增

**文件**: `src/graphrag/feedback.py` 新增方法

```python
async def _retrieve_cross_layer(self, missing_items: list[str], trace: ReasoningTrace) -> list:
    """每次反馈迭代都进行 L1→L2→L3 跨层检索"""
    all_nodes = []

    for item in missing_items:
        # L1: Component
        l1_nodes = self.retriever._retrieve_components(item, top_k=5)
        trace.cross_layer_expansion["l1_nodes"].extend(l1_nodes)

        # L1→L2: REFERENCE_OF
        for l1 in l1_nodes:
            l2_nodes = self.retriever.get_l2_references(l1.id, top_k=3)
            trace.cross_layer_expansion["l2_nodes"].extend(l2_nodes)

            # L2→L3: DEFINITION_OF
            for l2 in l2_nodes:
                l3_nodes = self.retriever.get_l3_definitions(l2.id, top_k=2)
                trace.cross_layer_expansion["l3_nodes"].extend(l3_nodes)

        all_nodes.extend(l1_nodes)
        all_nodes.extend(l2_nodes)
        all_nodes.extend(l3_nodes)

    return all_nodes
```

### 3.3 PlanGenerator 增强

**文件**: `src/graphrag/generator.py`

改动：prompt 中增加 chain-of-thought 要求，生成 `reasoning_chain` 字段：

```python
prompt = f'''...
请以JSON格式返回，包含steps数组，每个元素包含:
id, component, action, tool, safety_level, depends_on, confidence, evidence_ids, reasoning_chain

其中 reasoning_chain 是本步骤的推理过程字符串，描述：
1. 为什么选择这个部件
2. 为什么这个顺序是正确的
3. 证据来源是什么
'''
```

### 3.4 DuckDuckGo 联网搜索

**文件**: `src/graphrag/web_searcher.py`（新增）

```python
from duckduckgo_search import DDGS

class WebSearcher:
    def __init__(self):
        self.ddgs = DDGS()

    async def search(self, query: str, top_k: int = 5) -> List[Dict]:
        results = []
        for r in self.ddgs.text(query, max_results=top_k):
            results.append({
                "title": r["title"],
                "url": r["href"],
                "snippet": r["body"]
            })
        return results
```

### 3.5 NaturalLanguageFeedback 重构

**文件**: `src/graphrag/natural_feedback.py`

- `_retrieve_web()` 改为调用 `WebSearcher.search()`
- `generate_stream()` yield 中增加 `reasoning_trace` 事件

```python
async def generate_stream(self, question, use_web_search, context):
    ...
    if use_web_search:
        yield {"stage": "retrieving_web", "progress": 0.5}
        web_results = await self.web_searcher.search(question, top_k=5)
        trace.web_results = web_results
    yield {"stage": "reasoning", "progress": 0.75, "reasoning_trace": trace.to_dict()}
    ...
```

---

## 4. Schema 改动

### 4.1 Pydantic Schema 新增

**文件**: `src/api/schemas.py`

```python
class ReasoningChainItem(BaseModel):
    step_id: str
    reasoning: str
    evidence_sources: List[str]
    confidence_factors: Dict[str, float]
    cross_layer_depth: int  # 1=L1, 2=L2, 3=L3

class ConfidenceInfo(BaseModel):
    overall: float
    evidence_coverage: float
    cross_layer_depth_score: float
    consistency: float
    method: str = "0.5*coverage + 0.3*depth + 0.2*consistency"

class Step(BaseModel):
    ...
    reasoning_chain: Optional[List[ReasoningChainItem]] = []
    confidence_info: Optional[ConfidenceInfo] = None

class FeedbackResponse(BaseModel):
    plan: Dict
    reasoning_traces: List[Dict]  # 每轮迭代的 ReasoningTrace
    total_iterations: int
    final_confidence: float
```

### 4.2 API Response 示例

```json
{
  "plan": {
    "steps": [
      {
        "id": "1",
        "component": "upper_housing",
        "confidence": 0.85,
        "reasoning_chain": [
          {
            "step_id": "1",
            "reasoning": "上壳体是最外层结构，无需前置依赖。证据来源于 L2 文档 'Battery_Assembly_Guide' 中的步骤说明。",
            "evidence_sources": ["L2:doc:123", "L3:term:456"],
            "cross_layer_depth": 2
          }
        ]
      }
    ]
  },
  "reasoning_traces": [
    {
      "iteration": 0,
      "retrieved_nodes_count": 12,
      "cross_layer_expansion": {
        "l1": 5,
        "l2": 4,
        "l3": 3
      },
      "confidence_factors": {
        "evidence_coverage": 0.6,
        "cross_layer_depth": 0.7,
        "consistency": 0.8
      },
      "confidence": 0.67
    }
  ],
  "total_iterations": 2,
  "final_confidence": 0.82
}
```

---

## 5. 前端展示

### 5.1 推理链面板

在 `frontend/src/components/ReasoningChainPanel.tsx`（新增）：

```
迭代 1/3
├── 检索节点: 12个 (L1:5, L2:4, L3:3)
├── 置信度因子: coverage=0.6, depth=0.7, consistency=0.8
├── 综合置信度: 0.67
└── 缺失证据: ["thermal_management_system"]

迭代 2/3
├── 检索节点: 18个 (L1:8, L2:6, L3:4)
├── 置信度因子: coverage=0.85, depth=0.75, consistency=0.9
├── 综合置信度: 0.83
└── 缺失证据: []
```

### 5.2 GanttChart 增强

**文件**: `frontend/src/components/GanttChart.tsx`

在每个步骤的 tooltip 中展示：
- 该步骤的 `reasoning_chain`
- 该步骤的 `confidence_info`
- 跨层深度标识（★ L3）

---

## 6. 数据流

```
User Query
    │
    ▼
QueryRewriter
    │
    ▼
MultiPathRetriever ──────────────────────────────────┐
    │                                                 │
    ▼                                                 │
CrossLayerRetriever (初始触发)                        │
    L1 → L2 → L3                                     │
    │                                                 │
    ▼                                                 ▼
EvidenceRanker                              NaturalLanguageFeedback
    │                                          │         │
    ▼                                          ▼         ▼
PlanGenerator ◄──────── ReasoningTrace ◄── WebSearcher (DuckDuckGo)
    │                   (收集每轮)
    ▼
FeedbackLoop (迭代 1..N)
    │
    ├── _retrieve_cross_layer() ← 每次迭代都触发 L1→L2→L3
    │
    ▼
Regenerate → ReasoningTrace 记录
    │
    ▼
返回 plan + reasoning_traces[] + final_confidence
    │
    ▼
API Response + SSE流式前端展示
```

---

## 7. 实现步骤

### Phase 1: 核心基础设施
1. 新增 `src/graphrag/reasoning_trace.py` — `ReasoningTrace` 类
2. 新增 `src/graphrag/web_searcher.py` — `WebSearcher` + DuckDuckGo
3. Schema 改动：Pydantic model 新增字段

### Phase 2: FeedbackLoop 重构
4. `FeedbackLoop` 重构：引入 `ReasoningTrace`
5. 新增 `_retrieve_cross_layer()` 方法（L1→L2→L3 全链路）
6. 置信度因子计算方法

### Phase 3: Generator 增强
7. `PlanGenerator` prompt 增强：要求 reasoning_chain 输出
8. `EvidenceTracer` 改为内置到生成过程

### Phase 4: API + 前端
9. `natural_feedback.py` 接入 WebSearcher
10. SSE 流增加 reasoning_trace 事件
11. 新增 `ReasoningChainPanel.tsx`
12. `GanttChart.tsx` 增强展示

---

## 8. 测试计划

| 测试 | 验证 |
|------|------|
| 反馈迭代跨层 | FeedbackLoop 迭代后 L2/L3 节点数量增加 |
| 置信度计算 | evidence_coverage, cross_layer_depth, consistency 三个因子正确 |
| 联网搜索 | `_retrieve_web()` 返回非空列表 |
| 推理链展示 | API response 包含 `reasoning_traces` |
| 前端展示 | ReasoningChainPanel 正确渲染 |
