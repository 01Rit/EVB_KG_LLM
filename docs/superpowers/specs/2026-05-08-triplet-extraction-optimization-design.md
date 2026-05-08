# 三元组提取优化方案

## 问题

1. **抽取不稳定** — LLM 随机性 + Prompt 缺乏明确区分指引，导致同一文档多次抽取结果不一致
2. **关系类型混淆** — "是...的子部件"（结构）与"必须先于...拆卸"（顺序）被混用，产生虚假依赖
3. **虚假关系** — 生成不存在的拆卸路径，破坏图的连通性和可信度
4. **三专家评分无差异化**（独立 bug）— `batch_scorer.py:85` 硬传 `context = ''`，专家无组件上下文只能打泛泛的默认分

## 根因

| 问题 | 根因 |
|------|------|
| 抽取不稳定 | LLM 输出随机性；Prompt 示例不足 |
| 关系类型混淆 | Prompt 未明确区分"子部件关系"与"拆卸顺序关系"的语义边界 |
| 虚假关系 | Prompt 无约束条件，LLM 自由发挥 |
| 三专家评分无差异 | 传入 context 为空，LLM 只能对所有组件输出相似评分 |

## 方案

### 1. Prompt 优化（`src/importer/entity_extractor.py`）

**修改 `extract_triplets()` 的 prompt（第 45-81 行）**，增加：

#### 1.1 关系类型定义强化

在现有关系类型定义后，增加**语义边界说明**：

```
关系类型定义：
- "是...的子部件"：整体与部分的结构包含关系（静态）。例如：电池包-模组、模组-电芯。
  语义：表达"X 属于 Y 的一部分"，用于构建层级结构，不是操作序列。
- "必须先于...拆卸"：操作顺序的前后依赖（动态）。例如：盖板必须先于模组拆卸。
  语义：表达"如果不拆 X 就无法接触 Y"，用于确定拆卸路径。
```

#### 1.2 正例（Few-shot Examples）

在 prompt 末尾、JSON 输出前，增加：

```
【示例】

假设文档描述："拆卸Audi A3电池包，先拆上盖板，再拆绝缘层，最后取出模组"

正确抽取：
[
  {"head": "电池包", "tail": "模组", "relation": "是...的子部件"},
  {"head": "电池包", "tail": "上盖板", "relation": "是...的子部件"},
  {"head": "上盖板", "tail": "绝缘层", "relation": "必须先于...拆卸"},
  {"head": "绝缘层", "tail": "模组", "relation": "必须先于...拆卸"}
]

错误抽取（虚假关系）：
[
  {"head": "上盖板", "tail": "电芯", "relation": "必须先于...拆卸"}  ← 电芯与上盖板无直接拆卸路径
]

错误抽取（关系混淆）：
[
  {"head": "电池包", "tail": "模组", "relation": "必须先于...拆卸"}  ← 应为"是...的子部件"，不是拆卸顺序
]
```

#### 1.3 自检约束

在返回 JSON 前增加约束：

```
【返回前自检】
1. head 和 tail 是否为文档中明确提到的部件？
2. head → tail 的拆卸路径是否符合"逐步深入"原则？（外壳 → 覆盖件 → 模组 → 电芯）
3. 不要生成跨越多于一层级的依赖关系（如"上盖板 必须先于 电芯拆卸"）
4. 不要将结构包含关系误标为拆卸顺序
```

#### 1.4 层级路径约束

增加路径深度约束：

```
【层级约束】
拆卸路径通常是层层递进的：外壳 → 内部覆盖件 → 模组 → 电芯
相邻层级之间可以建立拆卸顺序关系，跳级关系应使用"是...的子部件"
```

### 2. 三专家评分 Context 补充（`src/allocator/batch_scorer.py`）

**修改 `score_component()` 方法（第 23-70 行）**：

从 Neo4j 查询组件已有属性作为 context：

```python
def score_component(self, component_name: str, battery_model: str = '',
                    context: str = '') -> Dict:
    # 如果 context 为空，从 Neo4j 查询组件上下文
    if not context and self.neo4j:
        component_data = self.neo4j.get_component_by_name(component_name, battery_model)
        if component_data:
            tool = component_data.get('tool_required', '未知')
            safety = component_data.get('safety_level', '未知')
            # 从 RELATES 关系中获取该组件的依赖节点和被依赖节点
            neighbors = self.neo4j.get_component_relationships(component_name, battery_model)
            context = f"部件名称：{component_name}，所需工具：{tool}，安全等级：{safety}，相关部件：{neighbors}"
    # ... 后续不变
```

**`Neo4jClient` 需新增方法** `get_component_by_name()` 和 `get_component_relationships()`。

如果 Neo4j 中无该组件信息，则使用备用 context：

```
"已知该部件为电池拆卸场景中的部件，拆卸工具通常为标准工具，安全风险为中等"
```

## 变更文件

| 文件 | 变更 |
|------|------|
| `src/importer/entity_extractor.py` | 修改 `extract_triplets()` 的 prompt，增加示例、约束、自检 |
| `src/allocator/batch_scorer.py` | 修改 `score_component()`，从 Neo4j 补充 context |
| `src/kg/client.py` | 新增 `get_component_by_name()` 和 `get_component_relationships()` |
| `tests/importer/test_entity_extractor.py` | 新增 `test_extract_triplets_with_improved_prompt()` |

## 验证方式

1. **Prompt 稳定性**：同文档调用 3 次，验证：
   - 输出 JSON 结构一致
   - 抽取的三元组数量差异 < 20%
   - 无虚假关系（如跨两层级的拆卸顺序）

2. **关系类型准确性**：构造包含"子部件"和"拆卸顺序"混用的测试文档，验证：
   - 结构关系使用"是...的子部件"
   - 顺序关系使用"必须先于...拆卸"
   - 无虚假跨层级依赖

3. **三专家评分差异化**：
   - 相同电池模型下，不同组件的 as_score 标准差 > 0.05
   - 同一组件三次调用，专家评分方差 > 0（应有差异）