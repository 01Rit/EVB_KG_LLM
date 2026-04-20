# 并行拆卸甘特图设计

**日期**: 2026-04-20
**状态**: 已批准
**版本**: v1.0

---

## 1. 概述

在序列规划界面新增甘特图，直观展示可并行拆卸的零件。甘特图按时间轴显示，同一时间阶段可并行的任务并排显示，体现拆卸过程中的并行作业关系。

### 1.1 目标

- 展示拆卸序列中可并行执行的零件
- 按时间轴显示任务执行顺序
- 用颜色区分人工/机器人任务
- 总工期由最长路径决定

### 1.2 约束

- 不引入新的前端依赖
- 甘特图仅用于展示（静态）
- 资源限制：1人 + 1机器人

---

## 2. 架构设计

### 2.1 数据流

```
GraphRAG → steps with depends_on
    ↓
topological_sort.get_parallel_groups() → 并行批次分组
    ↓
计算每批次的 start_time 和 duration
    ↓
API返回 parallel_batches
    ↓
前端GanttChart按批次渲染
```

### 2.2 资源分配规则

根据 `as_score` 和 `assignee` 决定任务分配：

| AS评分 | 分配 | 说明 |
|--------|------|------|
| AS > 0.6 | robot | 高风险任务由机器人执行 |
| AS < 0.4 | human | 低风险任务由人工执行 |
| 0.4 ≤ AS ≤ 0.6 | 根据loss决定 | 比较 human_loss 和 robot_loss |

---

## 3. 数据模型

### 3.1 API响应扩展

**现有响应结构**：
```json
{
  "data": {
    "steps": [...],
    "total_time_seconds": 752
  }
}
```

**扩展后响应结构**：
```json
{
  "data": {
    "steps": [...],
    "parallel_batches": [
      {
        "batch_id": 0,
        "tasks": ["upper housing"],
        "start_time": 0,
        "duration": 56
      },
      {
        "batch_id": 1,
        "tasks": ["upper transverse covers", "insulator"],
        "start_time": 56,
        "duration": 56
      }
    ],
    "total_time_seconds": 752
  }
}
```

### 3.2 TypeScript类型

```typescript
interface ParallelBatch {
  batch_id: number
  tasks: string[]  // 任务ID列表
  start_time: number  // 该批次开始时间(秒)
  duration: number  // 该批次持续时间=最长任务的duration
}

interface Step {
  id: number
  component: string
  component_name?: string
  depends_on: number[]
  time_seconds: number
  as_score?: number
  assignee?: 'human' | 'robot'
  // ... 其他字段
}
```

---

## 4. 并行批次计算

### 4.1 计算规则

1. **Batch 0**: 所有无依赖 (`depends_on = []`) 的任务
2. **Batch N**: 所有依赖已完成的更早批次任务的最早开始时间 = 前一批的 `start_time + duration`
3. **Batch duration**: 批次内最长任务的 `duration`
4. **总工期**: 所有批次的 `start_time + duration` 的最大值

### 4.2 算法

```python
def compute_parallel_batches(steps):
    # steps 按 id 排序
    batches = []
    processed = set()

    while len(processed) < len(steps):
        # 找所有依赖都已处理的任务
        current_batch = []
        for step in steps:
            if step['id'] in processed:
                continue
            deps = step.get('depends_on', [])
            if all(d in processed for d in deps):
                current_batch.append(step)

        if not current_batch:
            break

        # 计算当前批次的开始时间
        batch_start = 0
        for step in current_batch:
            for dep_id in step.get('depends_on', []):
                dep = find_step(dep_id)
                dep_end = dep['start_time'] + dep['duration']
                batch_start = max(batch_start, dep_end)

        # 批次duration = 最长任务的duration
        batch_duration = max(s['time_seconds'] for s in current_batch)

        # 分配任务到批次
        for step in current_batch:
            step['start_time'] = batch_start
            step['duration'] = batch_duration
            processed.add(step['id'])

        batches.append({
            'batch_id': len(batches),
            'tasks': [s['id'] for s in current_batch],
            'start_time': batch_start,
            'duration': batch_duration
        })

    return batches
```

---

## 5. 前端渲染

### 5.1 甘特图组件结构

```
GanttChart
├── Legend (图例)
│   ├── 灰色方块: 人工拆卸
│   └── 蓝色方块: 机器人拆卸
├── GanttHeader (时间轴)
│   └── TimeMarkers (刻度: 0s, 100s, 200s...)
└── GanttBody (主体)
    └── GanttBatch × N (每批次一行)
        ├── BatchLabel (批次标签)
        └── TaskBars (任务条并排)
```

### 5.2 样式规则

- 人工任务: 背景 `#6b7280` (灰色)
- 机器人任务: 背景 `#2563eb` (蓝色)
- 任务条高度: 24px
- 任务条间距: 4px
- 行高: 40px

### 5.3 布局计算

```
timeAxisWidth = 容器宽度 - 左侧标签宽度(150px)
marginLeft = (start_time / total_time) * timeAxisWidth
barWidth = (duration / total_time) * timeAxisWidth
```

---

## 6. 文件变更清单

### 后端
| 文件 | 变更 |
|------|------|
| `src/graphrag/planner.py` | 调用并行批次计算，返回 `parallel_batches` |

### 前端
| 文件 | 变更 |
|------|------|
| `frontend/src/types/index.ts` | `DisassemblyStep` 新增 `depends_on`，新增 `ParallelBatch` 接口 |
| `frontend/src/components/GanttChart.tsx` | 重构为按批次渲染，支持并行显示 |

---

## 7. 测试计划

### 7.1 后端测试
- [ ] 并行批次计算正确
- [ ] 批次开始时间正确（依赖前一批完成）
- [ ] 批次duration取最长任务
- [ ] API返回 `parallel_batches`

### 7.2 前端测试
- [ ] 甘特图按批次显示
- [ ] 同一批次任务并排显示
- [ ] 时间轴刻度正确
- [ ] 人工/机器人颜色正确

---

## 8. 依赖关系

- 现有 `topological_sort.get_parallel_groups()` 算法
- 现有 `as_score` 和 `assignee` 数据
- 现有 `depends_on` 依赖数据
