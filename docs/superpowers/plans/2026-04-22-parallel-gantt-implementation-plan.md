# 并行拆卸甘特图调度实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现正确的任务调度算法，人类任务和机器人任务在同一时间轴上并行显示

**Architecture:**
- 后端：根据资源约束（1人1机器人）计算每个任务的开始时间
- 前端：按序列顺序显示任务，每行一个任务

**Tech Stack:** Python FastAPI, React TypeScript

---

## Task 1: 修改后端调度算法

**Files:**
- Modify: `src/graphrag/planner.py`

- [ ] **Step 1: 修改 compute_parallel_batches 函数**

替换现有的 compute_parallel_batches 函数：

```python
def compute_parallel_batches(steps):
    """调度任务：人类串行，机器人串行，可并行"""
    if not steps:
        return []

    # 按id排序
    sorted_steps = sorted(steps, key=lambda s: s.get('id', 0))

    human_time = 0
    robot_time = 0

    for step in sorted_steps:
        duration = step.get('time_seconds', 0)
        assignee = step.get('assignee', 'human')

        if assignee == 'robot':
            step['start_time'] = robot_time
            robot_time += duration
        else:  # human
            step['start_time'] = human_time
            human_time += duration

        step['duration'] = duration

    return []
```

- [ ] **Step 2: 同步到Docker并测试**

```bash
docker cp src/graphrag/planner.py final414-backend-1:/app/src/graphrag/planner.py
docker restart final414-backend-1
```

- [ ] **Step 3: 运行测试**

```python
import requests
resp = requests.post('http://localhost:8000/api/v1/disassembly/plan',
    json={'battery_model': 'Audi_A3', 'context': [], 'debug': True}, timeout=120)
data = resp.json()
steps = data['data']['steps']
for s in steps[:5]:
    print(f"Step {s['id']}: start={s['start_time']}, dur={s['duration']}, assignee={s['assignee']}")
```

**预期输出：**
```
Step 1: start=0, dur=56, assignee=human
Step 2: start=0, dur=56, assignee=robot
Step 3: start=56, dur=37, assignee=human
Step 4: start=56, dur=56, assignee=robot
Step 5: start=93, dur=56, assignee=human
```

- [ ] **Step 4: 提交**

```bash
git add src/graphrag/planner.py
git commit -m "fix: implement correct resource scheduling for parallel GanttChart"
```

---

## Task 2: 前端GanttChart确认

**Files:**
- Modify: `frontend/src/components/GanttChart.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: 确认GanttChart使用steps的start_time**

检查 frontend/src/components/GanttChart.tsx 是否正确使用 step.start_time

```tsx
{steps.map((step) => {
  const startTime = step.start_time || 0
  const duration = step.time_seconds || 0
  const leftPercent = (startTime / totalTime) * 100
  // ...
})}
```

- [ ] **Step 2: 重建前端**

```bash
cd frontend && docker build -t final414-frontend:latest .
docker-compose up -d frontend
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/GanttChart.tsx frontend/src/index.css
git commit -m "fix: ensure GanttChart uses correct start_time positioning"
```

---

## 验证

**调度示例：**
```
A(人类,10s): start=0
B(机器人,5s): start=0
C(人类,8s): start=10  (等人类)
D(机器人,6s): start=5   (等机器人)
E(人类,12s): start=18  (等人类)
F(机器人,4s): start=11  (等机器人)
G(人类,7s): start=30   (等人类)
```

---

## 执行选项

**1. Subagent-Driven (推荐)** - 每任务派发子agent，任务间审核，快速迭代

**2. Inline Execution** - 本会话执行，批处理带检查点

选择哪个方式执行？