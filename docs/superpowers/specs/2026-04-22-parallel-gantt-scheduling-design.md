# 并行拆卸甘特图调度设计

**日期**: 2026-04-22
**状态**: 已批准
**版本**: v1.0

---

## 1. 需求理解

### 调度规则
- **任务顺序**：按拆卸序列顺序执行（不能改变顺序）
- **资源约束**：
  - 人类任务串行（1人）
  - 机器人任务串行（1台）
  - 人类和机器人可并行（不同资源）
- **开始时间**：等资源空闲

### 调度示例
```
序列：A>B>{C>D}>{E>F>G}
- A(人类,10s): start=0,   end=10
- B(机器人,5s): start=0,   end=5
- C(人类,8s):  start=10,  end=18  (等人类)
- D(机器人,6s): start=5,   end=11  (等机器人)
- E(人类,12s): start=18,  end=30  (等人类)
- F(机器人,4s): start=11,  end=15  (等机器人)
- G(人类,7s):  start=30,  end=37  (等人类)
```

---

## 2. 甘特图布局

### Y轴（行）
- 每行一个任务
- 按拆卸序列顺序排列（1, 2, 3, ...）
- 颜色区分：灰色=人类，蓝色=机器人

### X轴（时间）
- 共享时间轴（0s, 100s, 200s...）
- 时间刻度动态计算

---

## 3. 后端调度算法

### schedule_tasks 函数

```python
def schedule_tasks(steps):
    """调度任务：人类串行，机器人串行，可并行"""
    human_time = 0
    robot_time = 0

    for step in steps:  # 按id顺序
        duration = step.time_seconds
        assignee = step.assignee  # 'human' or 'robot'

        if assignee == 'robot':
            step.start_time = robot_time
            robot_time += duration
        else:  # human
            step.start_time = human_time
            human_time += duration

        step.duration = duration

    return steps
```

### 修改文件
- `src/graphrag/planner.py` - 修改 compute_parallel_batches 函数

---

## 4. 前端渲染

### GanttChart 组件
- 使用 steps 的 start_time 和 duration 计算位置
- X轴百分比：left = (start_time / totalTime) * 100
- Y轴：按任务顺序显示

### CSS
- 保持现有样式
- 时间轴刻度动态计算

---

## 5. 数据结构

### API响应
```json
{
  "data": {
    "steps": [
      {
        "id": 1,
        "component": "A",
        "assignee": "human",
        "time_seconds": 10,
        "start_time": 0,
        "duration": 10
      },
      ...
    ]
  }
}
```

---

## 6. 测试用例

```
输入序列：A>B>{C>D}>{E>F>G}
- A(人类): start=0
- B(机器人): start=0
- C(人类): start=10
- D(机器人): start=10
- E(人类): start=18
- F(机器人): start=14
- G(人类): start=30
```
