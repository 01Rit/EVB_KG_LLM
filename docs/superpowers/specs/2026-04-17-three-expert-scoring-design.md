# 三专家评分系统与AS计算设计

## 1. 概述

为Neo4j知识图谱节点增加三专家评分系统，通过LLM调用三个专家skill对L1层组件进行评分，使用熵权法计算最终H、S、AS得分，并将结果同步至节点属性，供拆卸序列规划使用。

## 2. 专家角色定义

| 专家 | 角色 | 评分范围 |
|------|------|----------|
| Expert A | 安全工程师 | H1-H5 + S1-S4 + 损伤因子 |
| Expert B | 生产工艺工程师 | H1-H5 + S1-S4 + 损伤因子 |
| Expert C | 质量检测专家 | H1-H5 + S1-S4 + 损伤因子 |

所有专家对所有因子（H1-H5, S1-S4, 损伤因子）进行评分，取平均后用熵权法计算最终得分。

## 3. 评分因子

### 3.1 人工操作难度因子 (H)

| 因子 | 符号 | 评分标准 |
|------|------|----------|
| Visibility | H1 | 0-3: 完全可见 → 完全遮挡 |
| Space Limitation | H2 | 0-3: 宽敞 → 完全限制 |
| Object Movement | H3 | 0-3: ≤1kg → ≥15kg |
| Ergonomic Impact | H4 | 0-3: 舒适 → 极度不适 |
| Repetitiveness | H5 | 0-3: <5次 → >30次 |

### 3.2 拆卸安全因子 (S)

| 因子 | 符号 | 评分标准 |
|------|------|----------|
| High-Voltage Risk | S1 | 0-3: 无风险 → 极高风险 |
| Chemical Reagent Risk | S2 | 0-3: 无风险 → 高风险 |
| Fire/Explosion Risk | S3 | 0-3: 无风险 → 高风险 |
| Human Injury Risk | S4 | 0-3: 无风险 → 高风险 |

### 3.3 拆卸损伤因子 (L)

| 因子 | 符号 | 评分标准 |
|------|------|----------|
| Human Disassembly Loss | Lh | 0-3: 无损失 → 严重损伤 |
| Machine Disassembly Loss | Lr | 0-3: 无损失 → 严重损伤 |

## 4. 熵权法计算流程

### 步骤1: 数据标准化
```
p_ij = x_ij / Σ(x_ij)
```

### 步骤2: 计算信息熵
```
E_j = -k * Σ(p_ij * ln(p_ij)), k = 1/ln(m)
```

### 步骤3: 计算权重
```
W_j = (1 - E_j) / Σ(1 - E_j)
```

### 步骤4: 计算综合得分

- **人工操作难度得分**: H = Σ(H_i × W_i)
- **拆卸安全得分**: S = Σ(S_i × w_i)
- **自动化得分**: AS = 0.5 × (H + S)

### 步骤5: 分配决策

- **AS > 0.6**: 推荐机器人(robot)
- **AS < 0.4**: 推荐人工(human)
- **0.4 ≤ AS ≤ 0.6**: 根据损失成本差决定，human_loss < robot_loss → human，反之 → robot

## 5. Neo4j节点新增属性

| 属性名 | 类型 | 说明 |
|--------|------|------|
| `expert_A_scores` | JSON | Expert A所有因子原始得分 |
| `expert_B_scores` | JSON | Expert B所有因子原始得分 |
| `expert_C_scores` | JSON | Expert C所有因子原始得分 |
| `h_weighted_score` | float | H加权得分 (0-1) |
| `s_weighted_score` | float | S加权得分 (0-1) |
| `as_score` | float | 自动化得分AS (0-1) |
| `human_loss` | float | 人工拆卸损失成本 (0-3) |
| `robot_loss` | float | 机器人拆卸损失成本 (0-3) |
| `loss_diff` | float | 损失成本差值 (human - robot) |
| `assignee` | string | human/robot |

## 6. API返回字段

```json
{
  "id": 1,
  "component": "电池壳体",
  "action": "拆卸外壳",
  "tool": ["螺丝刀", "扳手"],
  "h_score": 0.65,
  "s_score": 0.42,
  "as_score": 0.535,
  "human_loss": 2,
  "robot_loss": 1,
  "loss_diff": 1,
  "assignee": "human"
}
```

## 7. 实现组件

### 7.1 Expert Skills (LLM Prompts)
- `src/experts/safety_expert.py` - 安全工程师评分逻辑
- `src/experts/production_expert.py` - 生产工艺工程师评分逻辑
- `src/experts/quality_expert.py` - 质量检测专家评分逻辑

### 7.2 熵权法计算器
- `src/allocator/entropy_weight.py` - 熵权法权重计算

### 7.3 批量评分服务
- `src/allocator/batch_scorer.py` - 批量预计算L1组件评分

### 7.4 API扩展
- `src/api/schemas.py` - 新增返回字段
- `src/graphrag/planner.py` - 调用评分结果

## 8. 前端展示

拆卸序列页面显示：
- 基础信息：id、组件、操作、工具
- 综合得分：H得分、S得分、AS得分
- 损失成本：human_loss、robot_loss、loss_diff
- 分配结果：human/robot