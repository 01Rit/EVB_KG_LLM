# 拆卸序列甘特图设计

**日期**: 2026-04-20
**状态**: 已批准
**版本**: v1.0

---

## 1. 概述

在序列规划界面新增甘特图组件，直观展示拆卸序列的时间线、依赖关系和人工/机器人任务分配。

### 1.1 目标

- 可视化每个拆卸步骤的时间持续时长
- 展示步骤间的依赖关系
- 对比人工 vs 机器人的任务分配

### 1.2 约束

- 不引入新的前端依赖
- 甘特图仅用于展示（静态）
- 沿用现有配色方案（蓝色/灰色）

---

## 2. 架构设计

### 2.1 数据流

```
L1导入 → 三专家评估(扩展T因子) → 熵权法 → 存储time_score到Neo4j
                                                      ↓
前端请求 → /api/v1/disassembly/plan → 返回含time_seconds步骤
                                                      ↓
                                              GanttChart组件渲染
```

### 2.2 新增T因子评分维度

时间因子(Time Factor)由三专家分别评估：

**H_T (Human Time Factor)** - 安全工程师
- 体力操作时长
- 姿势保持时间
- 重复动作频率

**S_T (Safety Time Factor)** - 生产工艺工程师
- 高压暴露时长
- 化学品接触时长
- 热工作时长

**Q_T (Quality Time Factor)** - 质量检测工程师
- 精密操作时长
- 检测验证时长
- 清洁准备时长

---

## 3. 数据模型

### 3.1 Neo4j节点属性新增

```cypher
Component {
  ...
  # 现有字段
  as_score: Float,
  h_weighted_score: Float,
  s_weighted_score: Float,
  human_loss: Float,
  robot_loss: Float,

  # 新增字段
  t_score: Float,              # 综合时间评分 (0-3)
  h_time_factor: Float,         # H专家原始T因子
  s_time_factor: Float,        # S专家原始T因子
  q_time_factor: Float,        # Q专家原始T因子
  t_weighted_score: Float      # 熵权法加权T得分
}
```

### 3.2 API响应扩展

**GET/POST /api/v1/disassembly/plan**

响应中每个step新增字段：

```typescript
interface DisassemblyStep {
  id: number
  component: string
  component_name?: string
  action: string
  tool: string | string[]
  safety_level: number
  depends_on: number[]
  // 新增
  time_seconds: number         // 该步骤预计耗时(秒)
  // 现有评分字段
  as_score?: number
  h_score?: number
  s_score?: number
  human_loss?: number
  robot_loss?: number
  loss_diff?: number
  assignee?: 'human' | 'robot'
}

interface PlanResponse {
  battery_model: string
  steps: DisassemblyStep[]
  total_time_seconds: number   // 新增：总工期
  // 现有字段
  mode: 'local' | 'global'
  // ...
}
```

---

## 4. 实现细节

### 4.1 三专家T因子评估

**BaseExpert扩展**

`src/experts/base_expert.py` 中的评估因子列表扩展：

```python
FACTORS = [
    # 现有H因子
    'H1_visibility', 'H2_space_limitation', 'H3_object_movement',
    'H4_ergonomic_impact', 'H5_repetitiveness',
    # 现有S因子
    'S1_high_voltage', 'S2_chemical_reagent', 'S3_fire_explosion', 'S4_human_injury',
    # 现有D因子
    'Lh_human_loss', 'Lr_robot_loss',
    # 新增T因子
    'H_T',  # 体力操作时长因子
    'S_T',  # 安全风险时长因子
    'Q_T',  # 质量检测时长因子
]
```

**Prompt扩展**

在 `build_scoring_prompt` 中增加T因子评估说明：

```
评估部件 {component_name} 的时间因子:

H_T: 体力操作时长因子 (0-3)
  0 = 短暂操作(<10秒) 1 = 短时操作(10-30秒)
  2 = 中时操作(30-60秒) 3 = 长时间操作(>60秒)

S_T: 安全风险时长因子 (0-3)
  0 = 无暴露风险 1 = 短暂暴露(<10秒)
  2 = 中时暴露(10-30秒) 3 = 长期暴露(>30秒)

Q_T: 质量检测时长因子 (0-3)
  0 = 无需检测 1 = 快速检测(<10秒)
  2 = 标准检测(10-30秒) 3 = 复杂检测(>30秒)
```

### 4.2 熵权法扩展

**EntropyWeightCalculator**

`src/allocator/entropy_weight.py` 扩展：

```python
T_FACTORS = ['H_T', 'S_T', 'Q_T']

def calculate_t_score(self, expert_scores: List[Dict]) -> Dict:
    """计算综合时间评分"""
    # 提取T因子
    t_values = []
    for scores in expert_scores:
        t_factors = [max(0.0, min(3.0, scores.get(f, 1.5))) for f in self.T_FACTORS]
        t_values.append(t_factors)

    # 熵权计算
    weights = self._calculate_weights(t_values)

    # 加权求和
    weighted_t = []
    for scores in expert_scores:
        t_sum = sum(weights[i] * t_values[expert_scores.index(scores)][i]
                    for i in range(len(self.T_FACTORS)))
        weighted_t.append(t_sum)

    t_score = np.mean(weighted_t)

    return {
        't_score': round(t_score, 3),
        't_weighted_score': round(t_score, 3),  # 与t_score相同
        'h_time_factor': t_values[0],
        's_time_factor': t_values[1],
        'q_time_factor': t_values[2]
    }
```

### 4.3 MTM时间估算

**TimeEstimator扩展**

`src/sequence/time_estimator.py`：

```python
def estimate_from_component(self, component: Dict) -> int:
    """基于综合评分计算时间"""
    # 优先使用存储的time_score
    time_score = component.get('time_score', 1.5)

    # 获取工具系数
    tools = component.get('tool_required', [])
    tool_coef = self._get_tool_coefficient(tools)

    # 基础MTM时间
    base_time = (time_score / 3) * self.MTM_BASE_SECONDS

    # 时间 = 基础时间 * 工具系数
    time_seconds = int(base_time * tool_coef)

    return max(time_seconds, 5)  # 最小5秒

def _get_tool_coefficient(self, tools: List[str]) -> float:
    """根据工具类型返回时间系数"""
    if not tools or tools[0].lower() == 'none':
        return 1.0
    # screwdriver, wrench等基础工具
    return 1.2
```

### 4.4 L1导入时计算

**Importer扩展**

`src/importer/importer.py` 的 `_auto_score_component` 方法需要调用新的T因子评分流程：

```python
def _auto_score_component(self, component_name: str, battery_model: str) -> None:
    """L1导入时自动计算所有评分"""
    # ... 现有H, S, D评分逻辑 ...

    # 新增：T因子评分
    t_scores = self.scorer.score_time_factors(component_name, '')
    entropy_calc = EntropyWeightCalculator()
    t_result = entropy_calc.calculate_t_score([
        self.safety_expert.score(component_name, ''),
        self.production_expert.score(component_name, ''),
        self.quality_expert.score(component_name, '')
    ])

    # 更新Neo4j
    self.neo4j.update_component_properties(component_name, {
        'time_score': t_result['t_score'],
        'h_time_factor': t_result['h_time_factor'],
        's_time_factor': t_result['s_time_factor'],
        'q_time_factor': t_result['q_time_factor'],
        't_weighted_score': t_result['t_weighted_score']
    })
```

### 4.5 API响应扩展

**GraphRAG Planner**

`src/graphrag/planner.py` 的 `_enrich_steps_with_scores` 方法扩展：

```python
def _enrich_steps_with_scores(self, steps: list, battery_model: str) -> list:
    """Enrich steps with scoring data from Neo4j."""
    if not steps or not self._neo4j_client:
        return steps

    try:
        cypher = '''
        MATCH (c:Component {battery_model: $model})
        WHERE c.as_score IS NOT NULL
        RETURN c.id as id, c.name as name,
               c.as_score as as_score, c.h_weighted_score as h_score,
               c.s_weighted_score as s_score,
               c.time_score as time_score,
               c.human_loss as human_loss, c.robot_loss as robot_loss,
               c.loss_diff as loss_diff, c.assignee as assignee
        '''
        results = self._neo4j_client.execute_query(cypher, {'model': battery_model})
        # ... 现有匹配逻辑 ...

        # 计算time_seconds
        time_estimator = TimeEstimator()
        for step in enriched_steps:
            # 根据time_score计算实际时间
            time_score = step.get('time_score', 1.5)
            step['time_seconds'] = time_estimator.calculate_time_from_score(time_score)

        return enriched_steps
    except Exception as e:
        logger.warning(f'Failed to enrich steps with scores: {e}')
        return steps
```

**TimeEstimator新增方法**

```python
def calculate_time_from_score(self, time_score: float) -> int:
    """基于time_score计算时间秒数"""
    # 简化：直接用score映射
    base = (time_score / 3) * self.MTM_BASE_SECONDS
    return int(base)
```

---

## 5. 前端甘特图组件

### 5.1 组件结构

```
GanttChart
├── GanttHeader (时间轴)
│   └── TimeMarkers (刻度线: 0s, 30s, 60s, 90s...)
├── GanttBody (主体)
│   └── GanttRow × N
│       ├── TaskLabel (任务名)
│       ├── TaskBar (任务条)
│       └── DependencyArrow (依赖箭头，可选)
└── GanttLegend (图例)
```

### 5.2 样式规则

- 任务条背景：`#3b82f6` (蓝色)
- 任务条高度：24px
- 行高：40px
- 圆角：4px
- 文字：白色，12px

### 5.3 布局计算

```
totalWidth = 时间轴容器宽度
maxTime = total_time_seconds

任务条宽度 = (time_seconds / maxTime) * (totalWidth - 任务名宽度)
任务条左边距 = (startTime / maxTime) * (totalWidth - 任务名宽度)
```

---

## 6. 文件变更清单

### 后端
| 文件 | 变更 |
|------|------|
| `src/experts/base_expert.py` | 新增T因子定义和Prompt |
| `src/allocator/entropy_weight.py` | 新增calculate_t_score方法 |
| `src/sequence/time_estimator.py` | 新增calculate_time_from_score方法 |
| `src/graphrag/planner.py` | 扩展_enrich_steps_with_scores |
| `src/importer/importer.py` | 集成T因子评分到L1导入流程 |

### 前端
| 文件 | 变更 |
|------|------|
| `frontend/src/types/index.ts` | DisassemblyStep新增time_seconds |
| `frontend/src/pages/SequencePlanner.tsx` | 新增GanttChart组件 |

---

## 7. 测试计划

### 7.1 后端测试
- [ ] 三专家T因子评分正确返回
- [ ] 熵权法T得分计算正确
- [ ] API返回time_seconds字段
- [ ] L1导入时T因子计算并存储

### 7.2 前端测试
- [ ] 甘特图正确渲染
- [ ] 时间轴刻度正确
- [ ] 任务条宽度按比例显示
- [ ] 人工/机器人颜色区分

---

## 8. 依赖关系

- 现有三专家评分系统
- 现有熵权法计算
- 现有TimeEstimator
- 现有L1导入流程
