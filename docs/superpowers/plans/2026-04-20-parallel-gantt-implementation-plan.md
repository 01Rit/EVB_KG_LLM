# 并行拆卸甘特图实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在序列规划界面实现并行拆卸甘特图，按时间轴显示可并行执行的任务

**Architecture:**
- 后端：扩展GraphRAG Planner计算并行批次，返回 `parallel_batches` 字段
- 前端：重构GanttChart组件，按批次渲染并行任务

**Tech Stack:** Python FastAPI, React TypeScript, Neo4j

---

## 文件结构

```
src/
├── graphrag/
│   └── planner.py              # 计算并行批次，返回parallel_batches

frontend/src/
├── components/
│   └── GanttChart.tsx         # 重构为按批次渲染
├── pages/
│   └── SequencePlanner.tsx     # 集成甘特图
└── types/
    └── index.ts               # 新增ParallelBatch接口
```

---

## Task 1: 后端计算并行批次

**Files:**
- Modify: `src/graphrag/planner.py`
- Test: `tests/graphrag/test_planner.py` (如果存在)

### 算法说明

根据 steps 和 depends_on 计算并行批次：

```python
def compute_parallel_batches(steps):
    """计算并行批次"""
    # steps 已按 id 排序
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
                dep = next((s for s in steps if s['id'] == dep_id), None)
                if dep:
                    dep_end = dep.get('start_time', 0) + dep.get('time_seconds', 0)
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

### 实现步骤

- [ ] **Step 1: 添加 compute_parallel_batches 函数到 planner.py**

在 `src/graphrag/planner.py` 末尾添加：

```python
def compute_parallel_batches(steps):
    """根据depends_on计算并行批次"""
    if not steps:
        return []

    # 确保steps按id排序
    sorted_steps = sorted(steps, key=lambda s: s.get('id', 0))

    batches = []
    processed = set()

    while len(processed) < len(sorted_steps):
        current_batch = []
        for step in sorted_steps:
            if step['id'] in processed:
                continue
            deps = step.get('depends_on', [])
            if all(d in processed for d in deps):
                current_batch.append(step)

        if not current_batch:
            break

        batch_start = 0
        for step in current_batch:
            for dep_id in step.get('depends_on', []):
                dep = next((s for s in sorted_steps if s['id'] == dep_id), None)
                if dep:
                    dep_end = dep.get('start_time', 0) + dep.get('time_seconds', 0)
                    batch_start = max(batch_start, dep_end)

        batch_duration = max(s['time_seconds'] for s in current_batch)

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

- [ ] **Step 2: 在 _plan_local 方法中调用 compute_parallel_batches**

在 `src/graphrag/planner.py` 的 `_plan_local` 方法中，找到计算 `total_time_seconds` 的位置（约第166行），在其后添加：

```python
parallel_batches = compute_parallel_batches(steps)
total_time_seconds = max((b['start_time'] + b['duration'] for b in parallel_batches), default=0)
```

- [ ] **Step 3: 将 parallel_batches 添加到响应中**

修改 `_plan_local` 返回的 `result`（约第178行）：

```python
result = {
    'code': 0,
    'message': 'Success',
    'data': {
        'steps': steps,
        'parallel_batches': parallel_batches,
        'total_time_seconds': total_time_seconds,
        'mode': 'local'
    }
}
```

- [ ] **Step 4: 运行测试验证**

Run: `powershell -Command "cd 'D:\KG_project\Final4.14'; python -m pytest tests/graphrag/ -v"`
Expected: 现有测试通过

- [ ] **Step 5: 提交**

```bash
git add src/graphrag/planner.py
git commit -m "feat: add parallel batch computation for GanttChart"
```

---

## Task 2: 前端类型定义

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: 添加 ParallelBatch 接口**

在 `DisassemblyStep` 接口后添加：

```typescript
export interface ParallelBatch {
  batch_id: number
  tasks: number[]
  start_time: number
  duration: number
}
```

- [ ] **Step 2: 在 QueryResponseData 中添加 parallel_batches**

找到 `QueryResponseData` 接口，添加：

```typescript
parallel_batches?: ParallelBatch[]
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: add ParallelBatch type for GanttChart"
```

---

## Task 3: 重构GanttChart组件

**Files:**
- Modify: `frontend/src/components/GanttChart.tsx`

- [ ] **Step 1: 更新组件接收 parallel_batches**

```typescript
import { DisassemblyStep, ParallelBatch } from '../types'

interface GanttChartProps {
  steps: DisassemblyStep[]
  parallelBatches?: ParallelBatch[]
}
```

- [ ] **Step 2: 简化计算逻辑 - 直接使用 parallel_batches**

```typescript
export function GanttChart({ steps, parallelBatches }: GanttChartProps) {
  // 如果没有 parallel_batches，使用旧的串行方式
  if (!parallelBatches || parallelBatches.length === 0) {
    // 旧的串行渲染逻辑
    return <div>No parallel data</div>
  }

  const totalTime = Math.max(...parallelBatches.map(b => b.start_time + b.duration), 1)

  // 构建 stepId -> step 的映射
  const stepMap = new Map(steps.map(s => [s.id, s]))

  const timeMarkers: number[] = []
  const interval = Math.ceil(totalTime / 6)
  for (let t = 0; t <= totalTime; t += interval) {
    timeMarkers.push(t)
  }

  return (
    <div>
      <div className="gantt-legend">
        {/* 现有图例 */}
      </div>
      <div className="gantt-container">
        {/* 时间轴 */}
        <div className="gantt-header">
          <div className="gantt-label-col"></div>
          <div className="gantt-time-axis">
            {timeMarkers.map(t => (
              <div key={t} className="time-marker">{t}s</div>
            ))}
          </div>
        </div>
        {/* 批次行 */}
        <div className="gantt-body">
          {parallelBatches.map(batch => (
            <div key={batch.batch_id} className="gantt-row">
              <div className="gantt-label">
                Batch {batch.batch_id}
              </div>
              <div className="gantt-bar-container" style={{ display: 'flex', gap: '4px' }}>
                {batch.tasks.map(taskId => {
                  const step = stepMap.get(taskId)
                  if (!step) return null
                  const leftPercent = (batch.start_time / totalTime) * 100
                  const widthPercent = (batch.duration / totalTime) * 100
                  return (
                    <div
                      key={taskId}
                      className={`gantt-bar ${step.assignee === 'robot' ? 'robot' : 'human'}`}
                      style={{
                        marginLeft: `${leftPercent}%`,
                        width: `${Math.max(widthPercent, 2)}%`
                      }}
                      title={step.component_name || step.component}
                    >
                      {step.component_name || step.component}
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: 更新 SequencePlanner 中的调用**

在 `frontend/src/pages/SequencePlanner.tsx` 中：

```tsx
<GanttChart
  steps={result.data.steps}
  parallelBatches={result.data.parallel_batches}
/>
```

- [ ] **Step 4: 构建并测试**

Run: `cd frontend && npm run build`
Expected: 编译成功

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/GanttChart.tsx frontend/src/pages/SequencePlanner.tsx frontend/src/types/index.ts
git commit -m "feat: implement parallel GanttChart with batch rendering"
```

---

## Task 4: 集成测试

**Files:**
- 测试整个流程

- [ ] **Step 1: 同步后端代码到Docker**

```bash
docker cp src/graphrag/planner.py final414-backend-1:/app/src/graphrag/planner.py
docker restart final414-backend-1
```

- [ ] **Step 2: 重建前端**

```bash
cd frontend && docker build -t final414-frontend:latest .
docker-compose up -d frontend
```

- [ ] **Step 3: 验证API返回 parallel_batches**

```python
import requests
resp = requests.post('http://localhost:8000/api/v1/disassembly/plan',
    json={'battery_model': 'Audi_A3', 'context': [], 'debug': True}, timeout=120)
data = resp.json()
batches = data['data'].get('parallel_batches', [])
print(f"Parallel batches: {len(batches)}")
for b in batches:
    print(f"  Batch {b['batch_id']}: tasks={b['tasks']}, start={b['start_time']}, duration={b['duration']}")
```

Expected: 输出并行批次数据

- [ ] **Step 4: 前端实际渲染验证**

打开 http://localhost:9333
选择 Audi_A3 电池
点击生成序列
验证甘特图显示并行批次

- [ ] **Step 5: 提交所有更改**

```bash
git add -A
git commit -m "feat: complete parallel GanttChart implementation"
```

---

## 依赖关系

```
Task1 (后端并行批次) → Task4 (集成测试)
Task2 (前端类型) → Task3 (GanttChart组件)
Task3 (GanttChart组件) → Task4 (集成测试)
```

---

## 执行选项

**1. Subagent-Driven (推荐)** - 每任务派发子agent，任务间审核，快速迭代

**2. Inline Execution** - 本会话执行，批处理带检查点

选择哪个方式执行？