# Changelog v1.25

**发布日期**: 2026-05-14

---

## 核心修复

### 1. 依赖关系边方向修复（关键 Bug）

**问题**：数据库中关系 `BMC -> 冷却板`（BMC 先于冷却板拆卸）被错误解析，导致拓扑排序结果完全反向。

**修复**：
- `src/sequence/planner.py`: 修复 `dep_map[tail].append(head)` 方向
- `src/sequence/cycle_detector.py`: 修复 `graph.add_edge(dep, comp_id)` 边方向

**验证**：BMC → 冷却板，BMC → 冷却管 → 并行组：`[['BMC'], ['冷却板', '冷却管']]` ✓

### 2. 拓扑排序步骤 ID 字段

**问题**：前端 StepCard 使用 `step.id` 显示序号，但拓扑排序数据只有 `step.step` 字段。

**修复**：`src/sequence/planner.py` 添加 `'id': step_num` 字段

---

## 前端功能优化

### 3. 拓扑排序甘特图

**新增**：拓扑排序序列下方显示甘特图，与 LLM 序列并排展示

**文件**：`frontend/src/pages/SequencePlanner.tsx`

### 4. 并行零件文字标注

**新增**：在拆卸序列文字列表中标注可并行的零件

**示例**：`冷却板 (可并行: 冷却管)`

**文件**：`frontend/src/components/SequenceSection.tsx`, `StepCard.tsx`

### 5. 甘特图 Batch 颜色移除

**移除**：甘特图中 batch 背景色，保留人工/机器人任务条颜色

**文件**：`frontend/src/components/GanttChart.tsx`

---

## LLM Prompt 优化

### 6. 并行拆卸规则添加

**新增**：在 LLM 生成拆卸序列的 prompt 中添加并行拆卸规则

**规则**：
- 如果零件 A 的 depends_on 包含零件 B，则 A 必须在 B 之后拆卸
- 如果零件 A 和 B 彼此不在对方的 depends_on 中，且前置依赖已满足，则可以并行拆卸

**文件**：`src/graphrag/generator.py`

---

## 测试覆盖

- `tests/sequence/test_planner.py`: 新增 `test_parallel_disassembly_with_relations`, `test_topo_sort_steps_have_id`
- `tests/sequence/test_topological_sort.py`: 新增 `test_topological_sort_parallel_groups`

**测试结果**: 13/13 通过 ✓

---

## 提交记录

| Commit | 描述 |
|--------|------|
| `fce08d0` | fix(planner): correct dep_map direction for relation parsing |
| `e9a4c7a` | fix(cycle_detector): correct edge direction in graph construction |
| `f79bbca` | fix(planner): add id field to topo sort steps |
| `0afff99` | feat(generator): add parallel disassembly rules to prompt |
| `49df3b9` | fix(generator): improve parallel disassembly rules accuracy |
| `011d909` | style(gantt): remove batch background colors |
| `949d629` | feat(sequence): add parallel group labels to steps |
| `22db186` | feat(sequence): add gantt chart for topological sort results |

---

## 版本历史

- [v1.24](./CHANGELOG-v1.24.md) - 并行拆卸修复 + 甘特图批次可视化
- [v1.23](./CHANGELOG-v1.23.md) - 拓扑排序依赖标准化 + LLM时间合并
