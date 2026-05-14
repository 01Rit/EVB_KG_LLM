# 设计文档：前端展示优化

## 1. 概述

### 1.1 背景

当前系统存在两个前端展示问题：

1. **QueryPage 回答展示问题**
   - Markdown 文本未渲染，`**粗体**` 显示为原文
   - 来源标注 `【来源：本地KG-Component:绝缘体】` 未折叠，信息冗余

2. **SequencePlanner 单序列展示**
   - 只展示 LLM 生成序列
   - 用户希望同时对比拓扑排序序列和 LLM 序列

### 1.2 目标

- QueryPage：正确渲染 Markdown，来源标注可折叠
- SequencePlanner：同时展示拓扑排序和 LLM 生成两个序列

---

## 2. QueryPage 回答展示优化

### 2.1 设计决策

| 选择项 | 决定 | 理由 |
|--------|------|------|
| Markdown 渲染 | 使用 react-markdown | 成熟的 React Markdown 库 |
| 来源标注展示 | 默认折叠，点击展开 | 减少视觉噪音，信息按需获取 |
| 降级处理 | 解析失败保留原文 | 鲁棒性 |

### 2.2 组件设计

#### MarkdownRenderer

```tsx
interface MarkdownRendererProps {
  content: string
}
```

功能：
- 渲染 Markdown 文本
- 支持：粗体、斜体、列表、代码块、链接
- 粗体使用 `font-weight: 700`

#### CollapsibleSource

```tsx
interface SourceData {
  type: string      // e.g., "本地KG-Component"
  name: string      // e.g., "绝缘体"
  snippet?: string   // 证据片段
}

interface CollapsibleSourceProps {
  source: SourceData
  defaultCollapsed?: boolean
}
```

功能：
- 默认折叠状态，显示 `来源：{type}:{name}`
- 点击展开显示完整来源信息
- 样式：灰色背景，左侧蓝色边框

### 2.3 解析逻辑

从 LLM 回答中解析 `【来源：...】` 标注：

```
正则表达式: /【来源：([^】]+)】/g
```

示例：
- 输入：`根据资料【来源：本地KG-Component:绝缘体】显示...`
- 输出：拆分为文本片段和来源对象

---

## 3. SequencePlanner 双序列展示

### 3.1 设计决策

| 选择项 | 决定 | 理由 |
|--------|------|------|
| 布局方案 | 方案A（上下堆叠） | 清晰区分两种方法，窄屏友好 |
| API 调用 | 前端两次独立调用 | 后端改动小 |
| 推理链展示 | 折叠面板，点击展开 | 减少噪音，信息按需获取 |
| 置信度显示 | 精简版（百分比 + grade 标签） | 避免信息过载 |
| 甘特图 | 不改动 | 专注时序展示 |

### 3.2 布局结构

```
┌─────────────────────────────────────────────────────┐
│  🔵 拓扑排序序列                                      │
│  确定性 · 基于 precedence 规则                        │
├─────────────────────────────────────────────────────┤
│  Step 1: 上壳体 (Upper Housing)                      │
│  ⏱ 42s  👤 人工  AS: 0.32                          │
├─────────────────────────────────────────────────────┤
│  Step 2: 电池模组 (BMC)                             │
│  ⏱ 42s  🤖 机器人  AS: 0.19                        │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  🟡 LLM 生成序列                                    │
│  推理链 · 置信度评估                                │
├─────────────────────────────────────────────────────┤
│  Step 1: 上壳体 (Upper Housing)                     │
│  ⏱ 56s  👤 人工  置信度: 92%  [PASS]             │
│  [查看推理链 ▼]                                     │
├─────────────────────────────────────────────────────┤
│  🔗 推理链                                          │
│  ├─ L1: 上壳体为最外层组件，拆卸风险最低    0.92   │
│  │   证据: "Battery Pack Casing..."                │
│  └─ L2: 上壳体拆卸不需要前置步骤            0.88   │
│      证据: "根据文档描述..."                        │
│  综合推理：遵循先外层后内层的拆卸原则...             │
└─────────────────────────────────────────────────────┘
```

### 3.3 组件设计

#### SequenceSection

```tsx
interface SequenceSectionProps {
  title: string
  subtitle: string
  badge: 'topo' | 'llm'
  steps: DisassemblyStep[]
  showReasoningChain: boolean
  parallelBatches?: ParallelBatch[]
}
```

#### StepCard

```tsx
interface StepCardProps {
  step: DisassemblyStep
  showReasoningChain?: boolean
}
```

功能：
- 显示步骤基本信息
- LLM 序列额外显示置信度和 grade
- "查看推理链"按钮
- 折叠面板内嵌 ReasoningChainPanel

### 3.4 API 调用

```ts
// 同时调用两个端点
const [topoResult, llmResult] = await Promise.all([
  sequenceApi.getSequence(batteryModel),  // POST /api/v1/disassembly/sequence
  planApi.createPlan({ battery_model: batteryModel, context: [], debug: false })  // POST /api/v1/disassembly/plan
])
```

---

## 4. 文件清单

### 新增文件
- `frontend/src/components/MarkdownRenderer.tsx`
- `frontend/src/components/CollapsibleSource.tsx`
- `frontend/src/components/SequenceSection.tsx`
- `frontend/src/components/StepCard.tsx`

### 修改文件
- `frontend/src/pages/QueryPage.tsx`
- `frontend/src/pages/SequencePlanner.tsx`
- `frontend/src/components/ReasoningChainPanel.tsx`
- `frontend/src/api/client.ts`
- `frontend/package.json`

---

## 5. 依赖

```bash
cd frontend && npm install react-markdown
```

---

## 6. 验证标准

### QueryPage
- [ ] `**粗体**` 正确显示为粗体
- [ ] `【来源：本地KG-Component:xxx】` 默认折叠，点击展开

### SequencePlanner
- [ ] 拓扑排序序列显示在 LLM 序列上方
- [ ] LLM 序列的"查看推理链"按钮可点击展开
- [ ] 置信度百分比和 grade 标签正确显示
