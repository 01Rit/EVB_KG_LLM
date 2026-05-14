# v1.24 并行拆卸识别修复

## 修改内容

### 1. 修复并行拆卸调度算法 (src/graphrag/planner.py)

**`compute_parallel_batches` 函数：**
- **修复 assignee 为空值处理**: `step.get('assignee', 'human')` 在 DB 返回 `null` 时会返回 `None` 而非默认值 `'human'`，导致所有任务被识别为`None`，无法区分人机分工。修复为 `(step.get('assignee') or 'human')`。
- **修复依赖 ID 类型不匹配**: `depends_on` 中的 ID 与步骤 ID 类型可能不一致（int vs string），导致依赖解析失败。修复为统一使用 `str()` 比较。
- **新增 Debug 日志**: 记录每个步骤的 scheduling 决策（assignee、依赖、开始时间、串行时间线），便于排查并行调度问题。

**`_enrich_steps_with_scores` 函数：**
- **过滤空值合并**: DB 中为 `null` 的字段不再覆盖步骤已有属性，避免 `assignee: null` 等空值误写入步骤数据。

### 2. 前端甘特图并行批次可视化 (frontend/src/components/GanttChart.tsx)

- **新增并行批次提示栏**: 甘特图顶部显示各批次的概览（批次号、任务数、时长）。
- **批次底色区分**: 同一批次的任务行共享相同背景色，直观展示哪些零件可并行拆卸。
- **行标签增加批次号**: 每个任务名称前显示所属批次号（B1, B2, ...）。

## 影响范围

| 模块 | 影响 |
|------|------|
| 后端调度算法 | 修复并行识别逻辑，新增 logging |
| 前端甘特图 | 新增批次可视化、底色分组 |
| 版本号 | v1.23 → v1.24 |
