# 前端展示优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 优化 QueryPage 的 Markdown 渲染和来源折叠展示，同时为 SequencePlanner 添加双序列展示功能

**Architecture:** QueryPage 新增 MarkdownRenderer 和 CollapsibleSource 组件解析渲染回答；SequencePlanner 新增 SequenceSection 和 StepCard 组件实现双序列上下堆叠展示

**Tech Stack:** React, react-markdown, TypeScript

---

## 文件结构

```
frontend/src/
├── components/
│   ├── MarkdownRenderer.tsx       # 新增：Markdown 渲染
│   ├── CollapsibleSource.tsx      # 新增：可折叠来源
│   ├── SequenceSection.tsx        # 新增：序列区块容器
│   └── StepCard.tsx             # 新增：步骤卡片
├── pages/
│   ├── QueryPage.tsx             # 修改：使用新组件
│   └── SequencePlanner.tsx       # 修改：双序列展示
├── api/
│   └── client.ts                # 修改：添加 sequenceApi
└── types/
    └── index.ts                 # 已存在：类型定义
```

---

## Task 1: MarkdownRenderer 组件

**Files:**
- Create: `frontend/src/components/MarkdownRenderer.tsx`
- Test: `frontend/src/components/MarkdownRenderer.test.tsx` (手动验证)

- [ ] **Step 1: 创建 MarkdownRenderer 组件**

```tsx
// frontend/src/components/MarkdownRenderer.tsx
import ReactMarkdown from 'react-markdown'

interface MarkdownRendererProps {
  content: string
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <div style={{ lineHeight: '1.8' }}>
      <ReactMarkdown
        components={{
          p: ({ children }) => (
            <p style={{ marginBottom: '12px' }}>{children}</p>
          ),
          strong: ({ children }) => (
            <strong style={{ fontWeight: 700, color: '#1f2937' }}>{children}</strong>
          ),
          em: ({ children }) => (
            <em style={{ fontStyle: 'italic' }}>{children}</em>
          ),
          ul: ({ children }) => (
            <ul style={{ marginLeft: '20px', marginBottom: '12px', listStyleType: 'disc' }}>{children}</ul>
          ),
          ol: ({ children }) => (
            <ol style={{ marginLeft: '20px', marginBottom: '12px', listStyleType: 'decimal' }}>{children}</ol>
          ),
          li: ({ children }) => (
            <li style={{ marginBottom: '4px' }}>{children}</li>
          ),
          code: ({ children }) => (
            <code style={{
              backgroundColor: '#f3f4f6',
              padding: '2px 6px',
              borderRadius: '4px',
              fontFamily: 'monospace',
              fontSize: '14px'
            }}>{children}</code>
          ),
          pre: ({ children }) => (
            <pre style={{
              backgroundColor: '#1f2937',
              color: '#e5e7eb',
              padding: '12px',
              borderRadius: '8px',
              overflow: 'auto',
              marginBottom: '12px'
            }}>{children}</pre>
          ),
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer" style={{ color: '#3b82f6' }}>{children}</a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
```

- [ ] **Step 2: 验证组件可导入**

验证：在 SequencePlanner 中临时导入 MarkdownRenderer，确认无编译错误

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/MarkdownRenderer.tsx
git commit -m "feat(QueryPage): add MarkdownRenderer component"
```

---

## Task 2: CollapsibleSource 组件

**Files:**
- Create: `frontend/src/components/CollapsibleSource.tsx`

- [ ] **Step 1: 创建 CollapsibleSource 组件**

```tsx
// frontend/src/components/CollapsibleSource.tsx
import { useState } from 'react'

interface SourceData {
  type: string      // e.g., "本地KG-Component"
  name: string      // e.g., "绝缘体"
  snippet?: string   // 证据片段
}

interface CollapsibleSourceProps {
  source: SourceData
  defaultCollapsed?: boolean
}

export function CollapsibleSource({ source, defaultCollapsed = true }: CollapsibleSourceProps) {
  const [isExpanded, setIsExpanded] = useState(!defaultCollapsed)

  return (
    <div style={{
      backgroundColor: '#f9fafb',
      borderLeft: '3px solid #3b82f6',
      borderRadius: '4px',
      margin: '8px 0',
      overflow: 'hidden'
    }}>
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          padding: '8px 12px',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          userSelect: 'none'
        }}
      >
        <span style={{
          fontSize: '12px',
          color: '#6b7280',
          transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
          transition: 'transform 0.2s'
        }}>
          ▶
        </span>
        <span style={{ fontSize: '13px', color: '#374151' }}>
          来源：{source.type}: {source.name}
        </span>
      </div>
      {isExpanded && source.snippet && (
        <div style={{
          padding: '8px 12px',
          backgroundColor: '#fff',
          borderTop: '1px solid #e5e7eb',
          fontSize: '13px',
          color: '#4b5563'
        }}>
          {source.snippet}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/CollapsibleSource.tsx
git commit -m "feat(QueryPage): add CollapsibleSource component"
```

---

## Task 3: 修改 QueryPage 使用新组件

**Files:**
- Modify: `frontend/src/pages/QueryPage.tsx`

- [ ] **Step 1: 添加导入**

在文件顶部添加：

```tsx
import { MarkdownRenderer } from '../components/MarkdownRenderer'
import { CollapsibleSource } from '../components/CollapsibleSource'
```

- [ ] **Step 2: 添加解析函数**

在 QueryPage 组件定义之前添加：

```tsx
interface ParsedContent {
  type: 'text' | 'source'
  content: string
  source?: {
    type: string
    name: string
    snippet?: string
  }
}

function parseSources(content: string): ParsedContent[] {
  const parts: ParsedContent[] = []
  const regex = /【来源：([^】]+)】/g
  let lastIndex = 0
  let match

  while ((match = regex.exec(content)) !== null) {
    // 添加匹配之前的文本
    if (match.index > lastIndex) {
      parts.push({
        type: 'text',
        content: content.slice(lastIndex, match.index)
      })
    }

    // 解析来源
    const sourceStr = match[1]
    const colonIndex = sourceStr.indexOf(':')
    if (colonIndex > 0) {
      parts.push({
        type: 'source',
        content: '',
        source: {
          type: sourceStr.slice(0, colonIndex),
          name: sourceStr.slice(colonIndex + 1)
        }
      })
    }

    lastIndex = match.index + match[0].length
  }

  // 添加剩余文本
  if (lastIndex < content.length) {
    parts.push({
      type: 'text',
      content: content.slice(lastIndex)
    })
  }

  return parts
}
```

- [ ] **Step 3: 修改回答渲染逻辑**

找到回答渲染部分（约第 405-433 行）：

原代码：
```tsx
<div style={{
  background: '#fafafa',
  padding: '20px',
  borderRadius: '8px',
  borderLeft: '4px solid #3b82f6',
  marginBottom: '20px',
}}>
  <div style={{ lineHeight: '1.8', whiteSpace: 'pre-wrap' }}>
    {result.split('\n').map((line, i) => (
      <p key={i} style={{ marginBottom: '8px' }}>{line}</p>
    ))}
  </div>
</div>
```

替换为：
```tsx
<div style={{
  background: '#fafafa',
  padding: '20px',
  borderRadius: '8px',
  borderLeft: '4px solid #3b82f6',
  marginBottom: '20px',
}}>
  <MarkdownRenderer content={result} />
</div>
```

同时修改 sources 显示部分，使用 CollapsibleSource 组件：

找到 sources 显示部分（约第 435-453 行），替换为使用 CollapsibleSource。

- [ ] **Step 4: 验证**

运行前端开发服务器，检查 QueryPage 是否正确渲染 Markdown 和来源折叠

- [ ] **Step 5: 提交**

```bash
git add frontend/src/pages/QueryPage.tsx
git commit -m "feat(QueryPage): use MarkdownRenderer and CollapsibleSource"
```

---

## Task 4: SequenceSection 组件

**Files:**
- Create: `frontend/src/components/SequenceSection.tsx`

- [ ] **Step 1: 创建 SequenceSection 组件**

```tsx
// frontend/src/components/SequenceSection.tsx
import { DisassemblyStep, ParallelBatch } from '../types'

interface SequenceSectionProps {
  title: string
  subtitle: string
  badge: 'topo' | 'llm'
  steps: DisassemblyStep[]
  showReasoningChain: boolean
  parallelBatches?: ParallelBatch[]
}

export function SequenceSection({
  title,
  subtitle,
  badge,
  steps,
  showReasoningChain,
}: SequenceSectionProps) {
  const badgeStyle = badge === 'topo'
    ? { background: '#dbeafe', color: '#1d4ed8' }
    : { background: '#fef3c7', color: '#92400e' }

  return (
    <div className="card" style={{ marginBottom: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
        <span style={{
          ...badgeStyle,
          padding: '4px 12px',
          borderRadius: '12px',
          fontSize: '14px',
          fontWeight: 600
        }}>
          {badge === 'topo' ? '🔵 拓扑排序' : '🟡 LLM 生成'}
        </span>
        <span style={{ color: '#6b7280', fontSize: '13px' }}>{subtitle}</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {steps.map((step, idx) => (
          <StepCard
            key={step.id || idx}
            step={step}
            showReasoningChain={showReasoningChain}
          />
        ))}
      </div>
    </div>
  )
}

// 临时内联 StepCard，后续会独立组件
import { StepCard } from './StepCard'
```

注意：上述导入顺序有问题，应该修正为：

```tsx
// frontend/src/components/SequenceSection.tsx
import { useState } from 'react'
import { DisassemblyStep, ParallelBatch } from '../types'
import { StepCard } from './StepCard'

interface SequenceSectionProps {
  title: string
  subtitle: string
  badge: 'topo' | 'llm'
  steps: DisassemblyStep[]
  showReasoningChain: boolean
  parallelBatches?: ParallelBatch[]
}

export function SequenceSection({
  title,
  subtitle,
  badge,
  steps,
  showReasoningChain,
}: SequenceSectionProps) {
  const badgeStyle = badge === 'topo'
    ? { background: '#dbeafe', color: '#1d4ed8' }
    : { background: '#fef3c7', color: '#92400e' }

  return (
    <div className="card" style={{ marginBottom: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
        <span style={{
          ...badgeStyle,
          padding: '4px 12px',
          borderRadius: '12px',
          fontSize: '14px',
          fontWeight: 600
        }}>
          {badge === 'topo' ? '🔵 拓扑排序' : '🟡 LLM 生成'}
        </span>
        <span style={{ color: '#6b7280', fontSize: '13px' }}>{subtitle}</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {steps.map((step, idx) => (
          <StepCard
            key={step.id || idx}
            step={step}
            showReasoningChain={showReasoningChain}
          />
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/SequenceSection.tsx
git commit -m "feat(SequencePlanner): add SequenceSection component"
```

---

## Task 5: StepCard 组件

**Files:**
- Create: `frontend/src/components/StepCard.tsx`

- [ ] **Step 1: 创建 StepCard 组件**

```tsx
// frontend/src/components/StepCard.tsx
import { useState } from 'react'
import { DisassemblyStep } from '../types'
import { ReasoningChainPanel } from './ReasoningChainPanel'

interface StepCardProps {
  step: DisassemblyStep
  showReasoningChain?: boolean
}

function getGradeLabel(grade: string): string {
  switch (grade) {
    case 'PASS': return '✓ 通过'
    case 'WARN_CONSISTENCY': return '⚠ 一致性警告'
    case 'FAIL_DEPTH': return '✗ 深度不足'
    case 'FAIL_COVERAGE': return '✗ 证据不足'
    default: return grade || ''
  }
}

function getGradeColor(grade: string): string {
  switch (grade) {
    case 'PASS': return '#22c55e'
    case 'WARN_CONSISTENCY': return '#f59e0b'
    case 'FAIL_DEPTH': return '#ef4444'
    case 'FAIL_COVERAGE': return '#ef4444'
    default: return '#6b7280'
  }
}

export function StepCard({ step, showReasoningChain = false }: StepCardProps) {
  const [isReasoningExpanded, setIsReasoningExpanded] = useState(false)

  const assigneeColor = step.assignee === 'robot' ? '#8b5cf6' : '#10b981'
  const assigneeLabel = step.assignee === 'robot' ? '🤖 机器人' : '👤 人工'

  return (
    <div style={{
      display: 'flex',
      alignItems: 'flex-start',
      gap: '15px',
      padding: '15px',
      backgroundColor: '#fafafa',
      borderRadius: '8px',
      border: '1px solid #eee',
    }}>
      <div style={{
        width: '40px',
        height: '40px',
        borderRadius: '50%',
        backgroundColor: '#3b82f6',
        color: 'white',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 'bold',
        flexShrink: 0,
      }}>
        {step.id || step.step || '?'}
      </div>

      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>
          {step.component_name || step.component}
        </div>
        <div style={{ color: '#666', fontSize: '14px', marginBottom: '8px' }}>
          {step.action}
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', fontSize: '13px' }}>
          <span style={{ color: '#888' }}>⏱ {step.time_seconds}s</span>
          <span style={{ color: assigneeColor }}>{assigneeLabel}</span>
          {step.as_score !== undefined && (
            <span style={{
              padding: '2px 8px',
              borderRadius: '4px',
              backgroundColor: '#fee2e2',
              color: '#dc2626',
            }}>
              AS: {step.as_score.toFixed(3)}
            </span>
          )}
          {showReasoningChain && step.confidence !== undefined && (
            <span style={{ color: '#22c55e' }}>
              置信度: {(step.confidence * 100).toFixed(0)}%
            </span>
          )}
          {showReasoningChain && step.confidence_info && (
            <span style={{
              padding: '2px 6px',
              borderRadius: '4px',
              fontSize: '11px',
              fontWeight: 600,
              backgroundColor: getGradeColor(step.confidence_info.grade) + '20',
              color: getGradeColor(step.confidence_info.grade)
            }}>
              {getGradeLabel(step.confidence_info.grade)}
            </span>
          )}
        </div>

        {showReasoningChain && (
          <>
            <button
              onClick={() => setIsReasoningExpanded(!isReasoningExpanded)}
              style={{
                marginTop: '10px',
                padding: '6px 12px',
                backgroundColor: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '13px',
              }}
            >
              {isReasoningExpanded ? '收起推理链' : '查看推理链'}
            </button>

            {isReasoningExpanded && step.reasoning_chain && (
              <div style={{ marginTop: '12px' }}>
                <ReasoningChainPanel
                  reasoningTraces={[]}
                  totalIterations={0}
                  finalConfidence={step.confidence || 0}
                  stepReasoningChain={step.reasoning_chain}
                  stepConfidenceInfo={step.confidence_info}
                />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/StepCard.tsx
git commit -m "feat(SequencePlanner): add StepCard component"
```

---

## Task 6: 修改 ReasoningChainPanel 支持单步骤展示

**Files:**
- Modify: `frontend/src/components/ReasoningChainPanel.tsx`

- [ ] **Step 1: 添加新 Props 接口**

在文件顶部添加：

```tsx
interface StepReasoningChain {
  step_id: string
  links: ReasoningLink[]
  overall_reasoning: string
}

interface ConfidenceInfo {
  overall: number
  grade: string
  evidence_coverage: number
  cross_layer_depth_score: number
  consistency: number
  method: string
}
```

- [ ] **Step 2: 修改组件 Props**

原接口：
```tsx
interface ReasoningChainPanelProps {
  reasoningTraces: ReasoningTrace[]
  totalIterations: number
  finalConfidence: number
}
```

修改为：
```tsx
interface ReasoningChainPanelProps {
  reasoningTraces?: ReasoningTrace[]
  totalIterations?: number
  finalConfidence?: number
  // 新增：单步骤推理链
  stepReasoningChain?: StepReasoningChain
  stepConfidenceInfo?: ConfidenceInfo
}
```

- [ ] **Step 3: 添加单步骤渲染逻辑**

在组件内部，添加渲染单步骤推理链的逻辑：

```tsx
function renderStepReasoningChain(chain: StepReasoningChain, info?: ConfidenceInfo) {
  return (
    <div style={{ padding: '12px', backgroundColor: '#fffbeb', borderRadius: '8px' }}>
      {info && (
        <div style={{ marginBottom: '12px' }}>
          <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>
            综合置信度
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ flex: 1, height: '6px', background: '#e5e7eb', borderRadius: '3px' }}>
              <div style={{
                width: `${info.overall * 100}%`,
                height: '100%',
                background: info.overall >= 0.8 ? '#22c55e' : info.overall >= 0.6 ? '#f59e0b' : '#ef4444',
                borderRadius: '3px'
              }} />
            </div>
            <span style={{ fontSize: '12px', fontWeight: 600 }}>
              {info.overall.toFixed(2)}
            </span>
          </div>
        </div>
      )}

      <div style={{ marginBottom: '12px' }}>
        {chain.links.map((link, idx) => (
          <div key={idx} style={{
            background: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '6px',
            padding: '10px',
            marginBottom: '8px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <span style={{
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: '11px',
                fontWeight: 600,
                background: link.evidence_layer === 1 ? '#dbeafe' : link.evidence_layer === 2 ? '#fef3c7' : '#fce7f3',
                color: link.evidence_layer === 1 ? '#1d4ed8' : link.evidence_layer === 2 ? '#92400e' : '#9d174d'
              }}>
                L{link.evidence_layer}
              </span>
              <span style={{ fontSize: '13px', color: '#333' }}>{link.claim}</span>
              <span style={{ marginLeft: 'auto', fontSize: '12px', color: '#22c55e', fontWeight: 600 }}>
                {link.confidence.toFixed(2)}
              </span>
            </div>
            <div style={{ fontSize: '12px', color: '#666', background: '#f9f9f9', padding: '6px', borderRadius: '4px' }}>
              证据: {link.evidence_snippet?.slice(0, 100)}...
            </div>
          </div>
        ))}
      </div>

      {chain.overall_reasoning && (
        <div style={{
          fontSize: '13px',
          color: '#555',
          fontStyle: 'italic',
          paddingTop: '8px',
          borderTop: '1px dashed #ddd'
        }}>
          综合推理：{chain.overall_reasoning}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: 修改组件入口**

```tsx
export function ReasoningChainPanel({
  reasoningTraces,
  totalIterations,
  finalConfidence,
  stepReasoningChain,
  stepConfidenceInfo
}: ReasoningChainPanelProps) {
  // 如果有单步骤推理链，渲染单步骤版本
  if (stepReasoningChain) {
    return renderStepReasoningChain(stepReasoningChain, stepConfidenceInfo)
  }

  // 原有的迭代追踪渲染逻辑...
  // (保持不变)
}
```

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/ReasoningChainPanel.tsx
git commit -m "feat(SequencePlanner): extend ReasoningChainPanel for single step"
```

---

## Task 7: 修改 SequencePlanner 调用双 API

**Files:**
- Modify: `frontend/src/pages/SequencePlanner.tsx`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: 在 client.ts 添加 sequenceApi**

```ts
// frontend/src/api/client.ts
// 在现有 api 对象中添加
sequenceApi: {
  getSequence: (battery_model: string) => {
    return fetch('/api/v1/disassembly/sequence', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ battery_model }),
    }).then(res => res.json())
  },
},
```

- [ ] **Step 2: 修改 SequencePlanner 状态**

原状态：
```tsx
const [result, setResult] = useState<QueryResponse | null>(null)
```

修改为：
```tsx
const [topoResult, setTopoResult] = useState<any | null>(null)
const [llmResult, setLlmResult] = useState<QueryResponse | null>(null)
const [loading, setLoading] = useState(false)
```

- [ ] **Step 3: 修改 handleQuery 函数**

原逻辑：
```tsx
const handleQuery = async () => {
  // 单次调用 /api/v1/disassembly/plan
}
```

修改为：
```tsx
const handleQuery = async () => {
  if (!batteryModel.trim()) return

  setLoading(true)
  setTopoResult(null)
  setLlmResult(null)
  setProgress({ currentStep: 0, status: 'processing', message: '开始查询...' })

  try {
    // 同时调用两个 API
    const [topoRes, llmRes] = await Promise.all([
      sequenceApi.getSequence(batteryModel),
      queryApi.ask({
        battery_model: batteryModel,
        context: [],
        debug,
      })
    ])

    setTopoResult(topoRes)
    setLlmResult(llmRes.data)

    setProgress({
      currentStep: 5,
      status: 'success',
      message: '完成！',
    })
  } catch (error) {
    console.error('Query failed:', error)
    setProgress(prev => ({ ...prev, status: 'error', message: '推理失败' }))
  } finally {
    setLoading(false)
  }
}
```

- [ ] **Step 4: 修改渲染逻辑**

原渲染使用 `result?.data?.steps`，修改为两个 SequenceSection：

```tsx
<div>
  {topoResult && topoResult.data && topoResult.data.steps && topoResult.data.steps.length > 0 && (
    <SequenceSection
      title="拓扑排序序列"
      subtitle="确定性 · 基于 precedence 规则"
      badge="topo"
      steps={topoResult.data.steps}
      showReasoningChain={false}
      parallelBatches={topoResult.data.parallel_groups}
    />
  )}

  {llmResult && llmResult.steps && llmResult.steps.length > 0 && (
    <SequenceSection
      title="LLM 生成序列"
      subtitle="推理链 · 置信度评估"
      badge="llm"
      steps={llmResult.steps}
      showReasoningChain={true}
      parallelBatches={llmResult.parallel_batches}
    />
  )}

  {llmResult && llmResult.steps && llmResult.steps.length > 0 && (
    <GanttChart
      steps={llmResult.steps}
      parallelBatches={llmResult.parallel_batches || []}
    />
  )}
</div>
```

- [ ] **Step 5: 验证**

运行前端，检查两个序列是否正确显示

- [ ] **Step 6: 提交**

```bash
git add frontend/src/pages/SequencePlanner.tsx frontend/src/api/client.ts
git commit -m "feat(SequencePlanner): add dual sequence display with topological sort"
```

---

## Task 8: 最终验证

- [ ] **Step 1: QueryPage 验证**
- 打开 http://localhost:9333/query
- 输入问题，检查 Markdown 渲染和来源折叠

- [ ] **Step 2: SequencePlanner 验证**
- 打开 http://localhost:9333/sequence
- 选择电池型号，检查双序列展示

- [ ] **Step 3: 提交最终更改**

```bash
git add -A
git commit -m "feat: complete frontend display optimization"
```

---

## 验证清单

### QueryPage
- [ ] `**粗体**` 正确显示为粗体
- [ ] `【来源：本地KG-Component:xxx】` 默认折叠，点击展开

### SequencePlanner
- [ ] 拓扑排序序列显示在 LLM 序列上方
- [ ] LLM 序列的"查看推理链"按钮可点击展开
- [ ] 置信度百分比和 grade 标签正确显示
- [ ] 甘特图正常显示
