# 拆卸序列甘特图实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在序列规划界面新增甘特图组件，展示拆卸步骤的时间线、依赖关系和任务分配

**Architecture:**
- 后端：扩展三专家评分系统增加T因子(时间因子)，熵权法计算time_score，MTM估算实际时间
- 前端：纯CSS/HTML甘特图组件，使用现有steps数据渲染

**Tech Stack:** Python FastAPI, React TypeScript, Neo4j, MTM时间估算

---

## 文件结构

```
src/
├── experts/
│   └── base_expert.py          # T因子定义和Prompt
├── allocator/
│   └── entropy_weight.py       # calculate_t_score方法
├── sequence/
│   └── time_estimator.py       # calculate_time_from_score方法
├── graphrag/
│   └── planner.py              # 返回time_seconds
└── importer/
    └── importer.py             # L1导入时计算T因子

frontend/src/
├── pages/
│   └── SequencePlanner.tsx     # 新增GanttChart组件
└── types/
    └── index.ts                # DisassemblyStep新增time_seconds
```

---

## Task 1: 扩展BaseExpert添加T因子

**Files:**
- Modify: `src/experts/base_expert.py`
- Test: `tests/experts/test_base_expert.py`

- [ ] **Step 1: 检查现有T因子测试**

查看 `tests/experts/test_base_expert.py` 确认现有测试结构

- [ ] **Step 2: 添加T因子定义**

在 `base_expert.py` 的 `FACTORS` 列表中添加:
```python
# T因子 - 时间难度
'T_T',  # 时间因子(总)
```

- [ ] **Step 3: 扩展build_scoring_prompt添加T因子说明**

在prompt模板中添加T因子评估说明:
```
T_T: 时间难度因子 (0-3)
  0 = 短暂操作(<10秒) 1 = 短时操作(10-30秒)
  2 = 中时操作(30-60秒) 3 = 长时间操作(>60秒)
```

- [ ] **Step 4: 运行测试验证**

Run: `pytest tests/experts/test_base_expert.py -v`
Expected: 现有测试PASS

---

## Task 2: 扩展熵权法计算T得分

**Files:**
- Modify: `src/allocator/entropy_weight.py`
- Test: `tests/allocator/test_entropy_weight.py`

- [ ] **Step 1: 检查现有熵权测试结构**

```python
# 查看EntropyWeightCalculator类的方法和测试
```

- [ ] **Step 2: 添加T_FACTORS常量**

在 `EntropyWeightCalculator` 类中添加:
```python
T_FACTORS = ['H_T', 'S_T', 'Q_T']  # 时间因子列表
```

- [ ] **Step 3: 添加calculate_t_score方法**

```python
def calculate_t_score(self, expert_scores: List[Dict]) -> Dict[str, float]:
    """计算综合时间评分"""
    t_values = []
    for scores in expert_scores:
        t_factors = [max(0.0, min(3.0, scores.get(f, 1.5))) for f in self.T_FACTORS]
        t_values.append(t_factors)

    weights = self._calculate_weights(t_values)
    weighted_t = []
    for i, scores in enumerate(expert_scores):
        t_sum = sum(weights[j] * t_values[i][j] for j in range(len(self.T_FACTORS)))
        weighted_t.append(t_sum)

    t_score = np.mean(weighted_t)
    return {
        't_score': round(t_score, 3),
        'h_time_factor': t_values[0][0] if t_values else 1.5,
        's_time_factor': t_values[0][1] if t_values else 1.5,
        'q_time_factor': t_values[0][2] if t_values else 1.5
    }
```

- [ ] **Step 4: 添加单元测试**

```python
def test_calculate_t_score():
    calc = EntropyWeightCalculator()
    expert_scores = [
        {'H_T': 1.0, 'S_T': 1.5, 'Q_T': 2.0},
        {'H_T': 2.0, 'S_T': 1.0, 'Q_T': 1.5},
        {'H_T': 0.5, 'S_T': 2.0, 'Q_T': 1.0}
    ]
    result = calc.calculate_t_score(expert_scores)
    assert 't_score' in result
    assert 0 <= result['t_score'] <= 3
```

- [ ] **Step 5: 运行测试**

Run: `pytest tests/allocator/test_entropy_weight.py -v`
Expected: PASS

---

## Task 3: 扩展TimeEstimator计算时间

**Files:**
- Modify: `src/sequence/time_estimator.py`
- Test: `tests/sequence/test_time_estimator.py` (如果存在)

- [ ] **Step 1: 检查现有TimeEstimator实现**

```python
# 查看estimate_from_component方法和MTM_BASE_SECONDS
```

- [ ] **Step 2: 添加calculate_time_from_score方法**

```python
def calculate_time_from_score(self, time_score: float) -> int:
    """基于time_score计算时间秒数"""
    # 基础时间 = (score/3) * MTM_BASE_SECONDS
    base_time = (time_score / 3) * self.MTM_BASE_SECONDS
    return int(base_time)
```

- [ ] **Step 3: 修改estimate_from_component使用time_score**

```python
def estimate_from_component(self, component: Dict) -> int:
    # 优先使用存储的time_score
    time_score = component.get('time_score', 1.5)
    return self.calculate_time_from_score(time_score)
```

- [ ] **Step 4: 运行现有测试验证兼容性**

Run: `pytest tests/sequence/ -v`
Expected: PASS

---

## Task 4: 扩展GraphRAG Planner返回time_seconds

**Files:**
- Modify: `src/graphrag/planner.py`
- Test: `tests/graphrag/test_planner.py`

- [ ] **Step 1: 检查现有_enrich_steps_with_scores实现**

```python
# 查看当前如何获取scores数据
```

- [ ] **Step 2: 扩展Cypher查询添加time_score**

在 `_enrich_steps_with_scores` 的Cypher中添加:
```python
c.time_score as time_score,
```

- [ ] **Step 3: 添加time_seconds计算**

```python
time_estimator = TimeEstimator()
for step in enriched_steps:
    time_score = step.get('time_score', 1.5)
    step['time_seconds'] = time_estimator.calculate_time_from_score(time_score)
```

- [ ] **Step 4: 添加total_time_seconds到响应**

在返回数据中添加:
```python
total_time = sum(s['time_seconds'] for s in enriched_steps)
# 需要修改返回结构
```

- [ ] **Step 5: 运行测试验证**

Run: `pytest tests/graphrag/ -v`
Expected: PASS

---

## Task 5: 扩展L1导入计算T因子

**Files:**
- Modify: `src/importer/importer.py`
- Test: `tests/importer/test_importer.py` (如果存在)

- [ ] **Step 1: 检查现有_auto_score_component实现**

```python
# 查看如何调用scorer和更新Neo4j
```

- [ ] **Step 2: 扩展_update_component_with_scores**

在更新属性时添加T因子相关字段:
```python
# 添加 time_score, h_time_factor, s_time_factor, q_time_factor
```

- [ ] **Step 3: 运行导入测试验证**

```bash
# 如果有现有导入测试
pytest tests/importer/ -v
```

---

## Task 6: 前端添加GanttChart组件

**Files:**
- Create: `frontend/src/components/GanttChart.tsx`
- Modify: `frontend/src/pages/SequencePlanner.tsx`
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: 更新DisassemblyStep类型**

```typescript
export interface DisassemblyStep {
  id: number
  component: string
  component_name?: string
  action: string
  tool: string | string[]
  safety_level: number
  depends_on: number[]
  // 新增
  time_seconds: number
  as_score?: number
  h_score?: number
  s_score?: number
  human_loss?: number
  robot_loss?: number
  loss_diff?: number
  assignee?: 'human' | 'robot'
}
```

- [ ] **Step 2: 创建GanttChart组件**

```typescript
interface GanttChartProps {
  steps: DisassemblyStep[]
  totalTimeSeconds: number
}

function GanttChart({ steps, totalTimeSeconds }: GanttChartProps) {
  // 时间轴刻度计算
  const timeMarkers = []
  const interval = Math.ceil(totalTimeSeconds / 6) // 约6个刻度
  for (let t = 0; t <= totalTimeSeconds; t += interval) {
    timeMarkers.push(t)
  }

  return (
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
      {/* 任务行 */}
      <div className="gantt-body">
        {steps.map((step, idx) => (
          <div key={step.id || idx} className="gantt-row">
            <div className="gantt-label">
              {step.component_name || step.component}
            </div>
            <div className="gantt-bar-container">
              <div
                className={`gantt-bar ${step.assignee === 'robot' ? 'robot' : 'human'}`}
                style={{
                  width: `${(step.time_seconds / totalTimeSeconds) * 100}%`
                }}
              >
                {step.time_seconds}s
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: 添加甘特图样式**

```css
.gantt-container {
  margin-top: 20px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow-x: auto;
}
.gantt-header {
  display: flex;
  border-bottom: 1px solid #e5e7eb;
  background: #f9fafb;
}
.gantt-label-col {
  width: 150px;
  flex-shrink: 0;
}
.gantt-time-axis {
  display: flex;
}
.time-marker {
  min-width: 80px;
  padding: 8px;
  font-size: 12px;
  color: #666;
}
.gantt-row {
  display: flex;
  border-bottom: 1px solid #f3f4f6;
}
.gantt-row:last-child {
  border-bottom: none;
}
.gantt-label {
  width: 150px;
  padding: 8px;
  font-size: 13px;
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}
.gantt-bar-container {
  flex: 1;
  padding: 8px 0;
}
.gantt-bar {
  height: 24px;
  background: #3b82f6;
  border-radius: 4px;
  color: white;
  font-size: 12px;
  display: flex;
  align-items: center;
  padding: 0 8px;
  min-width: 40px;
}
.gantt-bar.robot {
  background: #2563eb;
}
.gantt-bar.human {
  background: #6b7280;
}
```

- [ ] **Step 4: 在SequencePlanner中集成GanttChart**

在 `steps.map` 下方添加:
```tsx
{result && result.data?.steps && result.data.steps.length > 0 && (
  <GanttChart
    steps={result.data.steps}
    totalTimeSeconds={result.data.total_time_seconds || 0}
  />
)}
```

- [ ] **Step 5: 构建并测试**

Run: `cd frontend && npm run build`
Expected: 编译成功

---

## Task 7: 集成测试

**Files:**
- Modify: `src/graphrag/planner.py`
- Modify: `src/sequence/time_estimator.py`

- [ ] **Step 1: 启动后端服务验证**

```bash
docker-compose up -d backend
# 等待启动完成
```

- [ ] **Step 2: 调用API验证响应**

```python
import requests
resp = requests.post('http://localhost:8000/api/v1/disassembly/plan',
    json={'battery_model': 'Audi_A3', 'context': [], 'debug': True})
data = resp.json()
# 验证 time_seconds 字段存在
step = data['data']['steps'][0]
assert 'time_seconds' in step
assert step['time_seconds'] > 0
```

- [ ] **Step 3: 前端实际渲染验证**

打开 http://localhost:9333
选择电池型号，点击生成序列
验证甘特图显示正确

---

## 依赖关系

```
Task1 (BaseExpert) → Task2 (熵权法)
Task2 (熵权法) → Task3 (TimeEstimator)
Task3 (TimeEstimator) → Task4 (Planner API)
Task4 (Planner API) → Task7 (集成测试)
Task1-3 → Task5 (L1导入)
Task4-5 → Task6 (前端甘特图)
```

---

## 执行选项

**1. Subagent-Driven (推荐)** - 每任务派发子agent，任务间审核，快速迭代

**2. Inline Execution** - 本会话执行，批处理带检查点

选择哪个方式执行？