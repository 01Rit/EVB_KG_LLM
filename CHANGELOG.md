# 拆卸序列规划优化与推理反馈模块 - 变更说明

> 版本: 1.0.0
> 日期: 2026-04-17
> 状态: 已完成

---

## 变更概述

本次变更实现了以下四个主要功能：

1. **拆卸序列规划优化** - 修复零件缺失和顺序问题
2. **电池型号搜索API** - 支持L1层电池型号模糊搜索
3. **KG+LLM推理反馈模块** - 通用问答系统，自然语言回答
4. **进度条** - SSE流式进度展示

---

## 1. 新增文件

### 1.1 `src/sequence/island_resolver.py`

**功能:** 孤立节点相似度匹配处理器

**类:**
- `SimilarityMatcher` - 基于Levenshtein编辑距离的名称相似度计算
- `IsolatedNodeResolver` - 解析孤立节点，尝试连接到相似节点

**接口:**
```python
class IsolatedNodeResolver:
    def resolve(self, isolated_nodes: List[str],
                all_nodes: List[str],
                existing_edges: List[Tuple[str, str]]) -> dict[str, Optional[str]]
```

**处理逻辑:**
1. 对每个孤立节点，遍历所有非孤立节点
2. 计算相似度得分（基于编辑距离）
3. 选择得分最高的节点建立虚拟依赖边
4. 如果最高分 < 阈值(0.3)，保留为独立步骤

---

### 1.2 `src/graphrag/natural_feedback.py`

**功能:** 自然语言反馈生成器 - 用于通用问答

**类:** `NaturalLanguageFeedback`

**进度阶段:**
```python
PROGRESS_STAGES = [
    ("understanding", "正在理解您的问题..."),
    ("retrieving_local", "正在检索本地知识库..."),
    ("retrieving_web", "正在检索网络资源..."),
    ("ranking", "正在排序证据..."),
    ("generating", "正在生成回答..."),
    ("done", "完成"),
]
```

**主要方法:**
- `generate_stream()` - SSE流式生成回答
- `generate_sync()` - 同步生成回答
- `_generate_answer()` - 生成带来源标注的自然语言回答

**来源标注格式:**
```
【来源：本地KG-Component:xxx】
【来源：本地KG-L2_Entity:xxx】
【来源：本地KG-L3_Term:xxx】
【来源：联网搜索:xxx】
```

---

### 1.3 测试文件

- `tests/sequence/test_island_resolver.py` - IsolatedNodeResolver测试
- `tests/graphrag/test_natural_feedback.py` - NaturalLanguageFeedback测试
- `tests/api/test_battery_routes.py` - 电池搜索API测试

---

## 2. 修改文件

### 2.1 `src/sequence/cycle_detector.py`

**问题:** `break_cycles()` 方法中删除孤立节点，导致零件缺失

**修改:** 移除第82行
```python
# 已删除
broken_graph.remove_nodes_from(list(nx.isolates(broken_graph)))
```

**影响:** 孤立节点现在会被保留作为独立拆卸步骤

---

### 2.2 `src/sequence/planner.py`

**修改1:** `_load_components()` 方法增强
- 新增查询RELATES关系
- 构建依赖映射

```python
# 新增查询
rel_cypher = '''
MATCH (c1:Component)-[r:RELATES]->(c2:Component)
WHERE c1.battery_model = $model AND r.type = '必须先于...拆卸'
RETURN c1.name as head, c2.name as tail, r.type as relation
'''
```

**修改2:** 新增 `_parse_components_with_relations()` 方法
- 解析组件和RELATIONS关系
- 合并precedence属性和RELATES关系构建完整依赖图

**修改3:** `plan()` 方法集成IsolatedNodeResolver
- 拓扑排序后处理孤立节点
- 为匹配成功的孤立节点添加虚拟边
- 重新排序确保正确顺序

---

### 2.3 `src/api/routes.py`

**新增端点:** `GET /api/v1/battery-models`

**参数:**
- `search` (string, optional): 模糊搜索电池型号
- `include_stats` (bool, default=true): 是否返回统计信息

**响应格式:**
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

---

### 2.4 `src/api/query_routes.py`

**新增端点:**

1. `POST /api/v1/query/feedback` - SSE流式问答
2. `POST /api/v1/query/feedback/sync` - 同步问答

**请求格式:**
```json
{
  "question": "磷酸铁锂电池有什么特点？",
  "use_web_search": false,
  "context": []
}
```

**SSE响应格式:**
```
data: {"stage": "understanding", "progress": 0.1, "message": "正在理解您的问题..."}
data: {"stage": "retrieving_local", "progress": 0.3, "message": "正在检索本地知识库..."}
...
data: {"stage": "done", "progress": 1.0, "message": "完成", "answer": "..."}
```

---

### 2.5 `src/config.py`

**问题:** settings初始化时未正确加载所有环境变量

**修改:** 新增 `load_settings()` 函数
```python
def load_settings():
    return Settings(
        neo4j_uri=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
        neo4j_user=os.getenv('NEO4J_USER', 'neo4j'),
        neo4j_password=os.getenv('NEO4J_PASSWORD', ''),
        ...
    )
```

---

## 3. API端点汇总

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/v1/battery-models` | GET | 搜索电池型号 |
| `/api/v1/query/feedback` | POST | SSE流式问答 |
| `/api/v1/query/feedback/sync` | POST | 同步问答 |

---

## 4. 数据流变更

### 拆卸序列规划

```
修改前:
Neo4j(Component) → precedence属性 → 拓扑排序 → 缺失零件

修改后:
Neo4j(Component) → precedence属性 + RELATES关系 → 完整依赖图
                                                       ↓
                                              孤立节点处理(IsolatedNodeResolver)
                                                       ↓
                                              虚拟边连接 → 拓扑排序 → 完整序列
```

### 问答反馈

```
用户问题 → 阶段1:理解 → 阶段2:本地检索 → 阶段3:排序 → 阶段4:生成 → 自然语言回答(带来源标注)
                    ↓
              SSE流式推送各阶段进度
```

---

## 5. 数据库查询变更

### RELATES关系查询

```cypher
-- 查询拆卸依赖关系
MATCH (c1:Component)-[r:RELATES]->(c2:Component)
WHERE c1.battery_model = $model AND r.type = '必须先于...拆卸'
RETURN c1.name as head, c2.name as tail
```

---

## 6. 配置要求

### 环境变量 (.env)

```env
NEO4J_URI=bolt://localhost:17687
NEO4J_USER=neo4j
NEO4J_PASSWORD=88888888
OPENAI_API_KEY=your_api_key
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

---

## 7. 测试覆盖

| 模块 | 测试数 | 状态 |
|------|--------|------|
| cycle_detector | 7 | ✅ |
| island_resolver | 2 | ✅ |
| planner | 6 | ✅ |
| time_estimator | 5 | ✅ |
| topological_sort | 4 | ✅ |
| natural_feedback | 3 | ✅ |

**单元测试总计: 27 passed**

---

## 8. 提交记录

| 提交 | 描述 |
|------|------|
| `66982cc` | feat: add IsolatedNodeResolver for similarity-based node matching |
| `afec95c` | fix: preserve isolated nodes instead of removing them |
| `da5edd9` | feat: load RELATES relations for disassembly sequence planning |
| `1a848a8` | feat: integrate IsolatedNodeResolver into disassembly planning |
| `8c70f4d` | feat: add battery model search API |
| `4e57ad3` | feat: add NaturalLanguageFeedback for Q&A module |
| `f6a4aa8` | fix: correct route paths in query_routes |
| `39dcbb8` | fix: correct component_name assertion in test |
| `bda0694` | fix: properly load settings from environment variables |
| `49e675a` | docs: add design and plan documents |

---

## 9. 前端集成说明

### 电池型号搜索

```typescript
// 调用API
const response = await fetch('/api/v1/battery-models?search=Audi&include_stats=true');
const data = await response.json();
// data.data[0].model, data.data[0].L1_components, etc.
```

### SSE进度条

```typescript
const eventSource = new EventSource('/api/v1/query/feedback', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ question: '...', use_web_search: false })
});

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.stage === 'done') {
    // 显示答案
  } else {
    // 更新进度条: data.progress, data.message
  }
};
```

### 来源切换

```typescript
// use_web_search = true/false 切换本地/联网
```

---

## 10. 已知限制

1. **联网搜索** - `use_web_search`参数暂未实现，返回空结果
2. **API集成测试** - 需要Neo4j运行在localhost:17687

---

## 11. 后续建议

1. 实现联网搜索功能（SerpAPI/DuckDuckGo）
2. 添加更丰富的相似度匹配策略（共现关系、组件类型）
3. 前端UI集成
4. 端到端测试覆盖
