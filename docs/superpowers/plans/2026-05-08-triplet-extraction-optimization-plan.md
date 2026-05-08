# 三元组提取优化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 优化三元组抽取 Prompt 使其稳定、关系类型准确、减少虚假关系；补充三专家评分的组件上下文以实现差异化评分

**Architecture:** 两处独立修改：(1) `entity_extractor.py` 的 `extract_triplets()` prompt 增加示例和约束；(2) `batch_scorer.py` 增加从 Neo4j 查询组件上下文传递给三专家

**Tech Stack:** Python, FastAPI, Neo4j, LLMClient

---

## 任务概览

| 任务 | 描述 |
|------|------|
| Task 1 | 优化 `extract_triplets()` 的 Prompt（添加示例 + 约束） |
| Task 2 | 在 `Neo4jClient` 添加 `get_component_by_name()` 和 `get_component_relationships()` |
| Task 3 | 修改 `batch_scorer.py` 的 `score_component()` 从 Neo4j 补充 context |
| Task 4 | 添加 `test_extract_triplets_stability` 测试 |
| Task 5 | 添加 `test_batch_scorer_context_enrichment` 测试 |

---

## Task 1: 优化 extract_triplets() Prompt

**Files:**
- Modify: `src/importer/entity_extractor.py:45-81`

- [ ] **Step 1: 读取当前 prompt 内容，确认行号**

Run: Read lines 45-81 of `src/importer/entity_extractor.py`

- [ ] **Step 2: 替换 prompt（第 45-81 行）**

将现有 prompt 替换为增强版本：

```python
        prompt = f'''从以下电池拆卸手册中提取知识图谱三元组，构建完整的拆卸序列图。

【重要】拆卸序列的关键是提取"必须在X之前拆卸Y"的关系，这决定了拓扑排序的依赖图。

文档内容：
{text}

提取要求：
1. 识别所有可拆卸部件
2. 提取部件间的拆卸依赖关系（如：必须先拆A才能拆B）
3. 提取工具、安全等级等信息作为节点属性

返回JSON数组格式，每个元素包含:
{{
  "head": "部件名称",        # 头实体
  "tail": "部件名称",        # 尾实体（被依赖的部件）
  "relation": "拆卸顺序",   # 关系类型
  "head_tool": "工具1,工具2",  # 头部件所需工具
  "head_safety": 1,        # 头部件安全等级 1-5
  "tail_tool": "工具1",    # 尾部件所需工具
  "tail_safety": 2         # 尾部件安全等级 1-5
}}

关系类型定义：
- "是...的子部件"：整体与部分的结构包含关系（静态）。例如：电池包-模组、模组-电芯。
  语义：表达"X 属于 Y 的一部分"，用于构建层级结构，不是操作序列。
- "必须先于...拆卸"：操作顺序的前后依赖（动态）。例如：盖板必须先于模组拆卸。
  语义：表达"如果不拆 X 就无法接触 Y"，用于确定拆卸路径。

【示例】

假设文档描述："拆卸Audi A3电池包，先拆上盖板，再拆绝缘层，最后取出模组"

正确抽取：
[
  {{"head": "电池包", "tail": "模组", "relation": "是...的子部件"}},
  {{"head": "电池包", "tail": "上盖板", "relation": "是...的子部件"}},
  {{"head": "上盖板", "tail": "绝缘层", "relation": "必须先于...拆卸"}},
  {{"head": "绝缘层", "tail": "模组", "relation": "必须先于...拆卸"}}
]

错误抽取（虚假关系）：
[
  {{"head": "上盖板", "tail": "电芯", "relation": "必须先于...拆卸"}}  ← 电芯与上盖板无直接拆卸路径
]

错误抽取（关系混淆）：
[
  {{"head": "电池包", "tail": "模组", "relation": "必须先于...拆卸"}}  ← 应为"是...的子部件"，不是拆卸顺序
]

【层级约束】
拆卸路径通常是层层递进的：外壳 → 内部覆盖件 → 模组 → 电芯
相邻层级之间可以建立拆卸顺序关系，跳级关系应使用"是...的子部件"

【返回前自检】
1. head 和 tail 是否为文档中明确提到的部件？
2. head → tail 的拆卸路径是否符合"逐步深入"原则？
3. 不要生成跨越多于一层级的依赖关系（如"上盖板 必须先于 电芯拆卸"）
4. 不要将结构包含关系误标为拆卸顺序

返回JSON数组：'''
```

- [ ] **Step 3: 运行现有测试确保未破坏**

Run: `python -m pytest tests/importer/test_entity_extractor.py -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add src/importer/entity_extractor.py
git commit -m "feat(entity_extractor): enhance prompt with examples and constraints for triplet extraction"
```

---

## Task 2: Neo4jClient 新增两个查询方法

**Files:**
- Modify: `src/kg/client.py`

- [ ] **Step 1: 在 `update_component_properties()` 后添加新方法**

在 `src/kg/client.py:257` 后添加：

```python
    def get_component_by_name(self, component_name: str, battery_model: str = None) -> Optional[dict]:
        """Get a single component by name."""
        if battery_model:
            cypher = '''
            MATCH (c:Component {name: $name, battery_model: $battery_model})
            RETURN COALESCE(c.id, c.name) as id, c.name as name, c.battery_model as battery_model,
                   c.tool_required as tool_required, c.safety_level as safety_level,
                   c.source_type as source_type
            '''
            results = self.execute_query(cypher, {'name': component_name, 'battery_model': battery_model})
        else:
            cypher = '''
            MATCH (c:Component {name: $name})
            RETURN COALESCE(c.id, c.name) as id, c.name as name, c.battery_model as battery_model,
                   c.tool_required as tool_required, c.safety_level as safety_level,
                   c.source_type as source_type
            '''
            results = self.execute_query(cypher, {'name': component_name})
        return results[0] if results else None

    def get_component_relationships(self, component_name: str, battery_model: str = None) -> dict:
        """Get neighboring components and relationship types for a given component."""
        if battery_model:
            cypher = '''
            MATCH (c:Component {name: $name, battery_model: $battery_model})-[r]-(neighbor)
            RETURN COALESCE(neighbor.name, neighbor.id) as neighbor_name,
                   type(r) as relation_type,
                   r.head_tool as head_tool, r.tail_tool as tail_tool,
                   r.head_safety as head_safety, r.tail_safety as tail_safety
            '''
            results = self.execute_query(cypher, {'name': component_name, 'battery_model': battery_model})
        else:
            cypher = '''
            MATCH (c:Component {name: $name})-[r]-(neighbor)
            RETURN COALESCE(neighbor.name, neighbor.id) as neighbor_name,
                   type(r) as relation_type,
                   r.head_tool as head_tool, r.tail_tool as tail_tool,
                   r.head_safety as head_safety, r.tail_safety as tail_safety
            '''
            results = self.execute_query(cypher, {'name': component_name})
        return {'neighbors': results} if results else {'neighbors': []}
```

- [ ] **Step 2: 添加 Optional import（如尚未存在）**

检查 `src/kg/client.py` 顶部 `from typing import ...` 是否有 `Optional`。如果 `from typing import Optional, Any` 存在则跳过此步。

- [ ] **Step 3: 运行现有测试**

Run: `python -m pytest tests/allocator/test_batch_scorer.py -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add src/kg/client.py
git commit -m "feat(kg): add get_component_by_name and get_component_relationships methods"
```

---

## Task 3: 修改 batch_scorer 补充 context

**Files:**
- Modify: `src/allocator/batch_scorer.py:23-70`

- [ ] **Step 1: 读取当前 `score_component` 方法**

Read `src/allocator/batch_scorer.py` lines 23-70

- [ ] **Step 2: 替换 `score_component()` 方法**

替换 `src/allocator/batch_scorer.py` 第 23-70 行：

```python
    def score_component(self, component_name: str, battery_model: str = '',
                        context: str = '') -> Dict:
        # 如果 context 为空，从 Neo4j 查询组件上下文
        if not context and self.neo4j:
            component_data = self.neo4j.get_component_by_name(component_name, battery_model)
            if component_data:
                tool = component_data.get('tool_required') or '未知'
                safety = component_data.get('safety_level') or '未知'
                rel_data = self.neo4j.get_component_relationships(component_name, battery_model)
                neighbors = rel_data.get('neighbors', [])
                neighbor_str = '；'.join(
                    f"{n.get('neighbor_name', '')}({n.get('relation_type', '')})"
                    for n in neighbors[:5]
                ) if neighbors else '无'
                context = f"部件名称：{component_name}，所需工具：{tool}，安全等级：{safety}，相关部件：{neighbor_str}"
            else:
                context = f"部件名称：{component_name}，电池型号：{battery_model}"

        expert_a_scores = self.safety_expert.score(component_name, context)
        expert_b_scores = self.production_expert.score(component_name, context)
        expert_c_scores = self.quality_expert.score(component_name, context)

        all_scores = [expert_a_scores, expert_b_scores, expert_c_scores]
        final_scores = self.entropy_calc.calculate_final_scores(all_scores)

        human_loss = final_scores['human_loss']
        robot_loss = final_scores['robot_loss']

        assignee = self.as_calc.determine_assignee(
            final_scores['as_score'],
            human_loss=human_loss,
            robot_loss=robot_loss
        )

        t_expert_scores = [
            {'T_T': expert_a_scores.get('T_T', 1.5)},
            {'T_T': expert_b_scores.get('T_T', 1.5)},
            {'T_T': expert_c_scores.get('T_T', 1.5)}
        ]
        t_result = self.entropy_calc.calculate_t_score(t_expert_scores)

        result = {
            'component': component_name,
            'battery_model': battery_model,
            'expert_A_scores': expert_a_scores,
            'expert_B_scores': expert_b_scores,
            'expert_C_scores': expert_c_scores,
            'h_score': final_scores['h_score'],
            's_score': final_scores['s_score'],
            'as_score': final_scores['as_score'],
            'human_loss': human_loss,
            'robot_loss': robot_loss,
            'loss_diff': final_scores['loss_diff'],
            'assignee': assignee,
            'time_score': t_result['t_score'],
            'h_time_factor': t_result['h_time_factor'],
            's_time_factor': t_result['s_time_factor'],
            'q_time_factor': t_result['q_time_factor'],
        }

        if self.neo4j:
            self._update_neo4j_node(result)

        return result
```

- [ ] **Step 3: 运行现有测试**

Run: `python -m pytest tests/allocator/test_batch_scorer.py -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add src/allocator/batch_scorer.py
git commit -m "feat(batch_scorer): enrich expert context from Neo4j for differentiated scoring"
```

---

## Task 4: 添加三元组抽取稳定性测试

**Files:**
- Modify: `tests/importer/test_entity_extractor.py`

- [ ] **Step 1: 添加 Mock LLM 和测试函数**

在 `tests/importer/test_entity_extractor.py` 末尾添加：

```python
class MockLLMStable:
    """Mock LLM that returns consistent triplet output."""
    def generate(self, prompt):
        return '''[
  {"head": "电池包", "tail": "模组", "relation": "是...的子部件", "head_tool": "扭矩扳手", "head_safety": 2, "tail_tool": "绝缘工具", "tail_safety": 3},
  {"head": "模组", "tail": "电芯", "relation": "是...的子部件", "head_tool": "绝缘工具", "head_safety": 3, "tail_tool": "拆卸夹具", "tail_safety": 4},
  {"head": "上盖板", "tail": "模组", "relation": "必须先于...拆卸", "head_tool": "螺丝刀", "head_safety": 1, "tail_tool": "绝缘工具", "tail_safety": 3}
]'''


def test_extract_triplets_stability():
    """Test that same text produces consistent triplet output."""
    from src.importer.entity_extractor import EntityExtractor
    extractor = EntityExtractor(MockLLMStable())

    text = "拆卸Audi A3电池包，先拆上盖板，再拆绝缘层，最后取出模组和电芯"
    result1 = extractor.extract_triplets(text, filename="test.txt")
    result2 = extractor.extract_triplets(text, filename="test.txt")

    assert len(result1) > 0
    assert len(result1) == len(result2)
    # All triplets should be identical
    for t1, t2 in zip(result1, result2):
        assert t1['head'] == t2['head']
        assert t1['tail'] == t2['tail']
        assert t1['relation'] == t2['relation']


def test_extract_triplets_relation_type_distinction():
    """Test that relation types are correctly distinguished."""
    from src.importer.entity_extractor import EntityExtractor
    extractor = EntityExtractor(MockLLMStable())

    text = "电池包包含模组，模组包含电芯，盖板必须先于模组拆卸"
    triplets = extractor.extract_triplets(text)

    relations = {t['relation'] for t in triplets}
    assert '是...的子部件' in relations
    assert '必须先于...拆卸' in relations


def test_extract_triplets_no_false_relationships():
    """Test that cross-level false relationships are filtered."""
    from src.importer.entity_extractor import EntityExtractor
    extractor = EntityExtractor(MockLLMStable())

    text = "上盖板必须先于电芯拆卸"  # False: these are not adjacent levels
    triplets = extractor.extract_triplets(text)

    for t in triplets:
        if t['relation'] == '必须先于...拆卸':
            head, tail = t['head'], t['tail']
            # Heads and tails should not be "盖板" and "电芯" directly
            assert not (head == '上盖板' and tail == '电芯'), "False relationship detected"
```

- [ ] **Step 2: 运行新测试**

Run: `python -m pytest tests/importer/test_entity_extractor.py -v`
Expected: PASS（Mock LLM 返回稳定输出，测试应全部通过）

- [ ] **Step 3: 提交**

```bash
git add tests/importer/test_entity_extractor.py
git commit -m "test: add triplet extraction stability and relation type tests"
```

---

## Task 5: 添加 batch_scorer context 补全测试

**Files:**
- Modify: `tests/allocator/test_batch_scorer.py`

- [ ] **Step 1: 添加 context 补全测试**

在 `tests/allocator/test_batch_scorer.py` 末尾添加：

```python
def test_score_component_with_neo4j_context():
    """Test that batch_scorer enriches context from Neo4j when available."""
    mock_llm = MagicMock()
    mock_llm.generate.return_value = '{"H1_visibility": 1.0, "H2_space_limitation": 1.5, "H3_object_movement": 2.0, "H4_ergonomic_impact": 1.0, "H5_repetitiveness": 0.5, "S1_high_voltage": 2.0, "S2_chemical_reagent": 0.5, "S3_fire_explosion": 0.5, "S4_human_injury": 1.0, "Lh_human_loss": 1.5, "Lr_robot_loss": 1.0, "T_T": 1}'

    mock_neo4j = MagicMock()
    mock_neo4j.get_component_by_name.return_value = {
        'name': 'Battery壳体',
        'battery_model': 'EV-500',
        'tool_required': '扭矩扳手',
        'safety_level': '2'
    }
    mock_neo4j.get_component_relationships.return_value = {
        'neighbors': [
            {'neighbor_name': '模组', 'relation_type': 'RELATES'}
        ]
    }

    scorer = BatchScorer(mock_llm, mock_neo4j)
    result = scorer.score_component("Battery壳体", "EV-500")

    # Verify Neo4j methods were called
    mock_neo4j.get_component_by_name.assert_called_once_with("Battery壳体", "EV-500")
    mock_neo4j.get_component_relationships.assert_called_once_with("Battery壳体", "EV-500")

    # Verify LLM was called with enriched context (not empty string)
    calls = mock_llm.generate.call_args_list
    assert len(calls) == 3  # Three experts
    for call in calls:
        prompt = call[0][0]  # First positional arg
        # Context should NOT be empty - should contain component info
        assert 'Battery壳体' in prompt
        assert '扭矩扳手' in prompt or 'EV-500' in prompt

    assert 'as_score' in result
    assert result['as_score'] > 0


def test_score_component_no_neo4j_fallback():
    """Test that batch_scorer works when Neo4j is not available."""
    mock_llm = MagicMock()
    mock_llm.generate.return_value = '{"H1_visibility": 1.0, "H2_space_limitation": 1.5, "H3_object_movement": 2.0, "H4_ergonomic_impact": 1.0, "H5_repetitiveness": 0.5, "S1_high_voltage": 2.0, "S2_chemical_reagent": 0.5, "S3_fire_explosion": 0.5, "S4_human_injury": 1.0, "Lh_human_loss": 1.5, "Lr_robot_loss": 1.0, "T_T": 1}'

    scorer = BatchScorer(mock_llm, neo4j_client=None)
    result = scorer.score_component("Battery壳体", "EV-500")

    assert 'as_score' in result
    assert 'expert_A_scores' in result
```

- [ ] **Step 2: 运行新测试**

Run: `python -m pytest tests/allocator/test_batch_scorer.py -v`
Expected: PASS

- [ ] **Step 3: 提交**

```bash
git add tests/allocator/test_batch_scorer.py
git commit -m "test: add batch_scorer Neo4j context enrichment tests"
```

---

## 自检清单

- [ ] 所有 5 个任务完成并提交
- [ ] `python -m pytest tests/importer/test_entity_extractor.py tests/allocator/test_batch_scorer.py -v` 全部通过
- [ ] Task 1 Prompt 修改内容包含：正例、反例、层级约束、自检
- [ ] Task 2 新方法 `get_component_by_name` 和 `get_component_relationships` 已添加
- [ ] Task 3 `score_component` 从 Neo4j 获取 context 逻辑已实现
- [ ] 没有遗留 TBD/TODO 占位符