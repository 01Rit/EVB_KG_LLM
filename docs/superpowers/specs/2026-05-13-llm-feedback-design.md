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

## 2.5 动态深度（混合路径 C）

**方案**：静态规则初筛 + LLM 仲裁，仅在边界模糊时调用 LLM

### 深度等级

| 等级 | 条件 | 行为 |
|------|------|------|
| Level 0 | `l1_coverage ≥ 0.65` **且** `len(l1_nodes) ≥ 10` | 不跨层，仅 L1 |
| Level 1 | `l1_coverage ∈ (0.10, 0.65)` 或 `len(l1_nodes) < 10` | L1→L2 |
| Level 2 | `l1_coverage ≤ 0.10` **或** 查询含 L3 关键词 | L1→L2→L3 |

> **注意**：阈值 0.65/0.10 为初始值，待收集真实 coverage 分布后调优。

### 灰色地带 LLM 仲裁

**灰色地带**：`0.10 < l1_coverage < 0.65` 时，调用轻量级 LLM 判断：

```
prompt: "分析查询：{query}，已有L1节点{L1_count}个，L2节点{L2_count}个。
判断是否需要深入L3：
0 = L1证据充足
1 = 需要L1→L2扩展
2 = 需要L1→L2→L3全链路
只返回数字0、1或2。"
```

### Coverage 分布采集（数据驱动阈值调优）

**目的**：通过日志采集真实 coverage 分布，用数据决定 0.10 和 0.65 这两个初始阈值的合理性。

**采集方式**：每次 `evaluate()` 调用时，将以下字段写入结构化日志：

```python
import structlog
logger = structlog.get_logger()

async def evaluate(self, evidence, intents):
    l1_coverage = self._calc_intent_coverage(evidence.l1_nodes, intents)
    l2_coverage = self._calc_intent_coverage(evidence.l2_nodes, intents)
    l3_coverage = self._calc_intent_coverage(evidence.l3_nodes, intents)
    l1_count = len(evidence.l1_nodes)

    depth = self._static_evaluate(l1_coverage, l1_count)  # 不调LLM的静态判断

    # 记录原始 coverage 值，用于事后分析
    logger.info("depth_evaluation",
        query_hash=hashlib.md5(query.encode()).hexdigest()[:8],
        l1_coverage=round(l1_coverage, 3),
        l2_coverage=round(l2_coverage, 3),
        l3_coverage=round(l3_coverage, 3),
        l1_count=l1_count,
        l2_count=len(evidence.l2_nodes),
        l3_count=len(evidence.l3_nodes),
        static_depth=depth,  # 静态初筛结果
        llm_arbitrated=(0.10 < l1_coverage < 0.65),  # 是否触发了LLM仲裁
        final_depth=depth,  # 最终决定
        battery_model=evidence.battery_model or "unknown",
    )

    return depth
```

**日志输出示例**（JSON Lines 格式）：

```
{"event":"depth_evaluation","l1_coverage":0.72,"l2_coverage":0.31,"l3_coverage":0.0,"l1_count":12,"l2_count":4,"l3_count":0,"static_depth":0,"llm_arbitrated":false,"battery_model":"Audi_A3"}
{"event":"depth_evaluation","l1_coverage":0.23,"l2_coverage":0.0,"l3_coverage":0.0,"l1_count":3,"l2_count":0,"l3_count":0,"static_depth":2,"llm_arbitrated":false,"battery_model":"Tesla_Model_3"}
{"event":"depth_evaluation","l1_coverage":0.45,"l2_coverage":0.15,"l3_coverage":0.0,"l1_count":7,"l2_count":2,"l3_count":0,"static_depth":1,"llm_arbitrated":true,"battery_model":"BMW_i3"}
```

**阈值调优方法**（约 2 周后数据分析）：

```python
# 伪代码：分析日志，确定最优阈值
import pandas as pd
import numpy as np

logs = pd.read_json("depth_evaluation_logs.jsonl", lines=True)

# 查看 coverage 分布直方图
logs["l1_coverage"].hist(bins=50)

# 分析 LLM 仲裁 vs 静态判断不一致的比例
mismatches = logs[logs["llm_arbitrated"] == True]

# 找到静态判断恰好在边界附近的样本（0.05~0.15 和 0.60~0.70）
boundary_low = logs[(0.05 < logs["l1_coverage"]) & (logs["l1_coverage"] < 0.15)]
boundary_high = logs[(0.60 < logs["l1_coverage"]) & (logs["l1_coverage"] < 0.70)]

# 观察这些样本的 LLM 最终决策，调整阈值
```

**阈值调整规则**：
- 若大部分 0.10~0.65 的 LLM 仲裁返回 0 或 2 → 扩大灰色地带
- 若大部分 LLM 仲裁与静态判断一致 → 缩小灰色地带，减少 LLM 调用

### 实现位置

新增 `src/graphrag/depth_evaluator.py`：

```python
class DepthEvaluator:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def evaluate(self, evidence: EvidenceGraph, intents: List[str]) -> int:
        l1_coverage = self._calc_intent_coverage(evidence.l1_nodes, intents)
        l1_count = len(evidence.l1_nodes)

        # 明确充足
        if l1_coverage >= 0.65 and l1_count >= 10:
            return 0

        # 明确不足 → 全链路
        if l1_coverage <= 0.10:
            return 2

        # 灰色地带 → LLM仲裁
        return await self._llm_arbitrate(evidence, intents)

    async def _llm_arbitrate(self, evidence, intents) -> int:
        prompt = f"""分析查询意图覆盖情况...
        已有L1节点{len(evidence.l1_nodes)}个，L2节点{len(evidence.l2_nodes)}个。
        返回0(L1足)、1(L1→L2)、2(L1→L2→L3)："""
        result = self.llm.generate(prompt).strip()
        return int(result) if result in ['0','1','2'] else 1
```

### 与 FeedbackLoop 的集成

```python
async def refine(self, ...):
    for iteration in range(self.max_iterations):
        trace = ReasoningTrace(query=query, iteration=iteration)

        # 动态深度评估（每次迭代）
        depth = await self.depth_evaluator.evaluate(evidence, intents)
        trace.target_depth = depth

        # 按深度执行跨层检索
        if depth >= 1:
            l1_nodes, l2_nodes = await self._retrieve_l1_l2(missing_evidence)
        if depth >= 2:
            l3_nodes = await self._retrieve_l3(l2_nodes)
        ...
```

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

### 3.2 跨层检索（动态深度）

**文件**: `src/graphrag/feedback.py` 新增/重构方法

```python
async def _retrieve_cross_layer(self, missing_items: list[str], trace: ReasoningTrace, depth: int) -> list:
    """按动态深度进行跨层检索"""
    all_nodes = []

    for item in missing_items:
        # L1: Component
        l1_nodes = self.retriever._retrieve_components(item, top_k=5)
        trace.cross_layer_expansion["l1_nodes"].extend(l1_nodes)
        all_nodes.extend(l1_nodes)

        if depth >= 1:
            # L1→L2: REFERENCE_OF
            for l1 in l1_nodes:
                l2_nodes = self._get_l2_nodes(l1.id, top_k=3)
                trace.cross_layer_expansion["l2_nodes"].extend(l2_nodes)
                all_nodes.extend(l2_nodes)

                if depth >= 2:
                    # L2→L3: DEFINITION_OF
                    for l2 in l2_nodes:
                        l3_nodes = self._get_l3_nodes(l2.id, top_k=2)
                        trace.cross_layer_expansion["l3_nodes"].extend(l3_nodes)
                        all_nodes.extend(l3_nodes)

    return all_nodes

def _get_l2_nodes(self, l1_id: str, top_k: int) -> list:
    """通过Neo4j查询L1→L2的REFERENCE_OF关系"""
    query = """
    MATCH (c)-[r:REFERENCE_OF]->(e:L2_Entity)
    WHERE c.id = $l1_id
    RETURN e.id as id, e.name as name, e.entity_type as entity_type,
           e.battery_model as battery_model, e.source_evidence as source_evidence
    LIMIT $top_k
    """
    return self.retriever.neo4j.execute(query, {"l1_id": l1_id, "top_k": top_k})

def _get_l3_nodes(self, l2_id: str, top_k: int) -> list:
    """通过Neo4j查询L2→L3的DEFINITION_OF关系"""
    query = """
    MATCH (e:L2_Entity)-[r:DEFINITION_OF]->(t:L3_Term)
    WHERE e.id = $l2_id
    RETURN t.id as id, t.name as name, t.definition as definition,
           t.source_evidence as source_evidence
    LIMIT $top_k
    """
    return self.retriever.neo4j.execute(query, {"l2_id": l2_id, "top_k": top_k})
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
2. 新增 `src/graphrag/depth_evaluator.py` — `DepthEvaluator` 类（动态深度评估器）
3. 新增 `src/graphrag/web_searcher.py` — `WebSearcher` + DuckDuckGo
4. Schema 改动：`src/api/schemas.py` Pydantic model 新增字段

### Phase 2: FeedbackLoop 重构
5. `FeedbackLoop` 重构：引入 `ReasoningTrace` 和 `DepthEvaluator`
6. 新增 `_retrieve_cross_layer()` 方法（按深度 L1→L2→L3）
7. 新增 `_get_l2_nodes()` / `_get_l3_nodes()` Neo4j 查询方法
8. 置信度因子计算方法 `_calc_confidence_factors()`

### Phase 3: Generator 增强
9. `PlanGenerator` prompt 增强：要求 reasoning_chain 输出
10. `EvidenceTracer` 改为内置到生成过程

### Phase 4: API + 前端
11. `natural_feedback.py` 接入 WebSearcher
12. SSE 流增加 reasoning_trace 事件
13. 新增 `frontend/src/components/ReasoningChainPanel.tsx`
14. `GanttChart.tsx` 增强展示

---

## 8. 测试计划

| 测试 | 验证 |
|------|------|
| 反馈迭代跨层 | FeedbackLoop 迭代后 L2/L3 节点数量增加 |
| 置信度计算 | evidence_coverage, cross_layer_depth, consistency 三个因子正确 |
| 联网搜索 | `_retrieve_web()` 返回非空列表 |
| 推理链展示 | API response 包含 `reasoning_traces` |
| 前端展示 | ReasoningChainPanel 正确渲染 |
