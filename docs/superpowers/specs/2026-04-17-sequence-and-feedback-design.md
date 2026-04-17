# 拆卸序列规划优化与推理反馈模块设计

## Status: APPROVED

## Date: 2026-04-17

## Overview

本设计针对以下四个需求进行优化：

1. **拆卸序列规划优化** - 修复零件缺失和顺序问题
2. **电池型号搜索API** - 支持L1层电池型号模糊搜索
3. **KG+LLM推理反馈模块** - 通用问答系统，自然语言回答
4. **进度条** - SSE流式进度展示

---

## Module 1: 拆卸序列规划优化

### Problem Analysis

**根因：**
- `_load_components()` 只查询 `precedence` 属性，没有查询 `RELATES` 关系
- `cycle_detector.py` 中 `remove_nodes_from(isolates())` 直接删除孤立节点
- 导致：零件缺失 + 顺序错误

**数据流问题：**
```
import_l1_txt() → 创建 RELATES 关系
     ↓
SequencePlanner._load_components() → 只查 precedence 属性
     ↓
依赖关系丢失！
     ↓
孤立节点被删除
     ↓
输出缺失零件
```

### Solution

#### 1.1 修改 `SequencePlanner._load_components()`

**原查询：**
```python
MATCH (c:Component {battery_model: $model})
RETURN c.id, c.name, c.precedence, ...
```

**新增查询 - 获取RELATES关系：**
```python
MATCH (c1:Component)-[r:RELATES]->(c2:Component)
WHERE c1.battery_model = $model AND r.type = '必须先于...拆卸'
RETURN c1.name as head, c2.name as tail, r.type as relation
```

**组件列表返回结构：**
```python
{
    'id': 'xxx',
    'name': 'upper_housing',
    'dependencies': ['insulator'],  # 从RELATES关系获取
    'precedence': [],  # 保留原属性
    ...
}
```

#### 1.2 修改 `CycleDetector.build_graph()`

**边方向：** `head → tail` 表示 head 在 tail 之前拆卸

```python
# 关系来源1: precedence 属性
for dep in dependencies:
    graph.add_edge(comp_id, dep)  # A依赖B → B→A

# 关系来源2: RELATES 关系 (新增)
for rel in relations:
    if rel['relation'] == '必须先于...拆卸':
        graph.add_edge(rel['head'], rel['tail'])
```

#### 1.3 移除删除孤立节点逻辑

**删除代码：**
```python
# cycle_detector.py line 82
broken_graph.remove_nodes_from(list(nx.isolates(broken_graph)))  # 删除
```

**替换为 - 调用 IsolatedNodeResolver：**

#### 1.4 新增 `IsolatedNodeResolver`

**文件：** `src/sequence/island_resolver.py`

**匹配策略（优先级）：**
1. **名称相似度** - 编辑距离算法，"upper_housing" ↔ "lower_housing"
2. **共现关系** - 曾在同一拆卸文档出现的零件
3. **组件类型** - 同类型零件优先连接 (housing/module/cell)

**接口：**
```python
class IsolatedNodeResolver:
    def resolve(self, isolated_nodes: list, all_nodes: list,
                existing_edges: list) -> dict[str, str | None]:
        """
        Returns: {isolated_id: connected_id} 或 {isolated_id: None}
        """
```

**处理流程：**
1. 对每个孤立节点，遍历所有非孤立节点
2. 计算相似度得分
3. 选择得分最高的节点建立虚拟依赖边
4. 如果最高分 < 阈值，保留为独立步骤（不删除）

---

## Module 2: 电池型号搜索API

### API Endpoint

**端点：** `GET /api/v1/battery-models`

**Query参数：**
- `search` (string, optional): 模糊匹配电池型号
- `include_stats` (bool, default=true): 是否返回统计信息

### Response Format

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "model": "Audi_A3",
      "L1_components": 15,
      "L2_entities": 50,
      "L3_terms": 20
    }
  ]
}
```

### Implementation

**Cypher查询：**
```python
# 基础查询 - 获取不同型号
MATCH (c:Component)
WHERE c.battery_model CONTAINS $search
RETURN DISTINCT c.battery_model as model

# 统计L1
WITH model
MATCH (c:Component {battery_model: model})
RETURN model, count(c) as L1_components

# 统计L2 (通过RELATES或CONTAINS关系)
OPTIONAL MATCH (c:Component {battery_model: model})
<-[:REFERENCED_IN|...]-(e:L2_Entity)
RETURN model, count(DISTINCT e) as L2_entities
```

---

## Module 3: KG+LLM推理反馈模块（问答系统）

### API Endpoint

**端点：** `POST /api/v1/query/feedback`

**Streaming:** `text/event-stream` (SSE)

### Request

```json
{
  "question": "磷酸铁锂电池有什么特点？",
  "use_web_search": false,
  "context": []
}
```

### SSE Progress Stages

```
1. "正在理解您的问题..."
2. "正在检索本地知识库..." (L1+L2+L3)
3. "正在检索网络资源..." (如果use_web_search=true)
4. "正在排序证据..."
5. "正在生成回答..."
```

### Response Format (Non-Streaming)

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "answer": "磷酸铁锂电池（LiFePO4）是一种...\n\n1. 安全性能优异...\n\n【来源：本地KG-L2_Entity:LiFePO4_cell】\n【来源：本地KG-L3_Term:cycle_life】",
    "sources": [
      {"type": "L2_Entity", "name": "LiFePO4_cell", "evidence": "..."},
      {"type": "L3_Term", "name": "cycle_life", "definition": "..."}
    ]
  }
}
```

### Source Attribution Format

```
【来源：本地KG-Component:xxx】
【来源：本地KG-L2_Entity:xxx】
【来源：本地KG-L3_Term:xxx】
【来源：联网搜索:xxx】
```

### Implementation

**新增文件：**
- `src/graphrag/natural_feedback.py` - 自然语言反馈生成器

**修改文件：**
- `src/api/query_routes.py` - 添加SSE端点

**核心类：**
```python
class NaturalLanguageFeedback:
    def __init__(self, retriever, ranker, llm_client):
        ...

    async def generate(
        self,
        question: str,
        use_web_search: bool,
        context: list[str]
    ) -> AsyncGenerator[dict, None]:
        """SSE generator yielding progress and final result"""
```

---

## Module 4: 前端改动

### Battery Model Search

**位置：** 拆卸计划页面 - 电池型号选择器

**交互：**
1. 下拉框 + 模糊搜索
2. 显示每个型号的统计信息 (L1/L2/L3数量)
3. 用户选择后加载对应零件数据

### Source Toggle

**位置：** 问答反馈页面

**交互：**
- 按钮切换: "本地知识库" / "本地+联网"
- 图标指示当前模式

### SSE Progress Bar

**位置：** 问答反馈页面 - 答案生成区域

**交互：**
- 实时显示当前阶段
- 进度条动画
- 完成后收起/淡出

---

## File Changes Summary

### New Files

| File | Description |
|------|-------------|
| `src/sequence/island_resolver.py` | 孤立节点相似度匹配 |
| `src/graphrag/natural_feedback.py` | 自然语言反馈生成器 |

### Modified Files

| File | Changes |
|------|---------|
| `src/sequence/planner.py` | _load_components() 增加RELATES查询 |
| `src/sequence/cycle_detector.py` | 移除删除孤立节点逻辑 |
| `src/api/query_routes.py` | 添加SSE端点 |
| `src/api/routes.py` | 添加电池搜索API |

---

## Dependencies

- Neo4j: Component, RELATES, L2_Entity, L3_Term 节点
- LLM: GPT-4 for natural language generation
- 可选: SerpAPI for web search

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| 孤立节点匹配质量差 | 设置相似度阈值，低于阈值保留为独立步骤 |
| SSE连接中断 | 前端重连机制 + 超时处理 |
| LLM幻觉 | 来源标注让用户可验证 |
