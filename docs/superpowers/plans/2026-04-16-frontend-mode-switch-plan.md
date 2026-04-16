# 前端模式切换实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 4.16 迭代的 local/global 模式功能同步至前端 QueryPage

**Architecture:** 在 QueryPage 添加标签切换、响应区分展示、调试信息增强

**Tech Stack:** React, TypeScript, CSS

---

## 文件结构

```
frontend/
├── src/
│   ├── types/index.ts          # 添加 mode 类型
│   ├── api/client.ts           # 添加 mode 参数
│   └── pages/QueryPage.tsx     # 标签切换、响应区分、调试增强
```

---

## Task 1: 更新 Types 定义

**Files:**
- Modify: `frontend/src/types/index.ts:20-27`

- [ ] **Step 1: 修改 QueryResponse 类型**

```typescript
// 修改 frontend/src/types/index.ts 中的 QueryResponse
export interface QueryResponse {
  code: number
  message: string
  data: {
    steps?: DisassemblyStep[]      // local 模式
    response?: string             // global 模式
    mode?: 'local' | 'global'
    trace?: QueryTrace
  }
}
```

- [ ] **Step 2: 编译验证**

Run: `python -m py_compile frontend/src/types/index.ts` (仅验证 ts 文件语法)
Expected: 无语法错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat(frontend): add mode type to QueryResponse"
```

---

## Task 2: 更新 API Client

**Files:**
- Modify: `frontend/src/api/client.ts:14-18`

- [ ] **Step 1: 修改 QueryRequest 类型并更新 API 调用**

```typescript
// 修改 frontend/src/api/client.ts 中的 QueryRequest 和 queryApi

export interface QueryRequest {
  battery_model: string
  context: string[]
  debug: boolean
  mode?: 'local' | 'global'  // 添加 mode 参数
}

export const queryApi = {
  ask: (data: QueryRequest) => api.post<QueryResponse>('/disassembly/plan', data),
  getHistory: (limit = 10) => api.get('/query/history', { params: { limit } }),
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat(frontend): add mode parameter to queryApi"
```

---

## Task 3: 更新 QueryPage 组件

**Files:**
- Modify: `frontend/src/pages/QueryPage.tsx:1-185`

- [ ] **Step 1: 添加 mode state 和标签切换 UI**

在 `export function QueryPage()` 函数内，添加：

```typescript
const [mode, setMode] = useState<'local' | 'global'>('local')
```

在电池型号输入后添加标签切换：

```tsx
<div style={{ marginBottom: '20px' }}>
  <label style={{ display: 'block', marginBottom: '10px', fontWeight: 'bold' }}>
    查询模式
  </label>
  <div style={{ display: 'flex', gap: '10px' }}>
    <button
      onClick={() => setMode('local')}
      style={{
        padding: '10px 20px',
        backgroundColor: mode === 'local' ? '#3b82f6' : '#fff',
        color: mode === 'local' ? '#fff' : '#333',
        border: '1px solid #ddd',
        borderRadius: '8px',
        cursor: 'pointer',
      }}
    >
      本地检索
    </button>
    <button
      onClick={() => setMode('global')}
      style={{
        padding: '10px 20px',
        backgroundColor: mode === 'global' ? '#3b82f6' : '#fff',
        color: mode === 'global' ? '#fff' : '#333',
        border: '1px solid #ddd',
        borderRadius: '8px',
        cursor: 'pointer',
      }}
    >
      全局查询
    </button>
  </div>
</div>
```

- [ ] **Step 2: 更新 API 调用传递 mode 参数**

修改 `handleQuery` 函数中的 API 调用：

```typescript
const res = await queryApi.ask({
  battery_model: batteryModel,
  context,
  debug,
  mode,  // 添加 mode 参数
})
```

- [ ] **Step 3: 添加响应格式区分展示**

修改结果展示部分：

```tsx
{result && (
  <div className="card">
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <h2>结果</h2>
        <span style={{
          padding: '4px 12px',
          borderRadius: '4px',
          fontSize: '12px',
          fontWeight: 'bold',
          background: result.data?.mode === 'global' ? '#f0fdf4' : '#e0f2fe',
          color: result.data?.mode === 'global' ? '#15803d' : '#0369a1',
        }}>
          {result.data?.mode === 'global' ? '全局查询' : '本地检索'}
        </span>
      </div>
      {/* 导出按钮保留 */}
    </div>

    {/* 响应格式区分 */}
    {result.data?.mode === 'global' ? (
      <div style={{ 
        background: '#fafafa', 
        padding: '20px', 
        borderRadius: '8px',
        borderLeft: '4px solid #3b82f6'
      }}>
        <h3 style={{ marginBottom: '10px' }}>AI 回答</h3>
        <p style={{ lineHeight: '1.6' }}>{result.data.response}</p>
      </div>
    ) : (
      /* 本地模式的步骤表格保持不变 */
      <div style={{ marginBottom: '20px' }}>
        <h3>拆卸步骤</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '10px' }}>
          <thead>
            <tr style={{ backgroundColor: '#f5f5f5' }}>
              <th style={{ padding: '10px', textAlign: 'left' }}>序号</th>
              <th style={{ padding: '10px', textAlign: 'left' }}>组件</th>
              <th style={{ padding: '10px', textAlign: 'left' }}>操作</th>
              <th style={{ padding: '10px', textAlign: 'left' }}>工具</th>
              <th style={{ padding: '10px', textAlign: 'left' }}>置信度</th>
            </tr>
          </thead>
          <tbody>
            {steps.map((step) => (
              <tr key={step.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: '10px' }}>{step.id}</td>
                <td style={{ padding: '10px' }}>{step.component}</td>
                <td style={{ padding: '10px' }}>{step.action}</td>
                <td style={{ padding: '10px' }}>{step.tool?.join(', ') || '-'}</td>
                <td style={{ padding: '10px' }}>{((step.confidence || 0) * 100).toFixed(0)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}

    {/* 调试面板增强 */}
    {debug && result.data?.trace && (
      <div>
        <h3>推理过程（Debug）</h3>
        <div style={{ backgroundColor: '#f5f5f5', padding: '15px', borderRadius: '8px', marginTop: '10px' }}>
          <p><strong>查询模式:</strong> {result.data.mode}</p>
          <p><strong>重写查询:</strong> {result.data.trace.rewritten_queries?.join(', ')}</p>
          <p><strong>检索路径:</strong> {result.data.trace.retrieval_paths?.join(', ')}</p>
          <p><strong>证据数量:</strong> {result.data.trace.evidence_count}</p>
          <p><strong>迭代次数:</strong> {result.data.trace.iteration_count}</p>
          {result.data.trace.timing && (
            <>
              <p><strong>Timing:</strong></p>
              <ul style={{ marginLeft: '20px' }}>
                <li>重写: {result.data.trace.timing?.rewrite_ms}ms</li>
                <li>检索: {result.data.trace.timing?.retrieve_ms}ms</li>
                <li>生成: {result.data.trace.timing?.generate_ms}ms</li>
                <li>反馈: {result.data.trace.timing?.feedback_ms}ms</li>
                <li>总计: {result.data.trace.timing?.total_ms}ms</li>
              </ul>
            </>
          )}
        </div>
      </div>
    )}
  </div>
)}
```

- [ ] **Step 4: 更新 steps 变量定义**

由于全局模式没有 steps，需要更新 steps 变量的定义位置：

```typescript
// 在组件内部，将 steps 定义移到条件判断之前
const steps: DisassemblyStep[] = result?.data?.steps || []
```

- [ ] **Step 5: 编译验证**

Run: 验证 React 组件语法无错误

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/QueryPage.tsx
git commit -m "feat(frontend): add mode switch and response handling"
```

---

## 验收检查清单

- [ ] Task 1: Types 定义更新完成
- [ ] Task 2: API Client 更新完成
- [ ] Task 3: QueryPage 组件更新完成
- [ ] 标签切换可切换 local/global 模式
- [ ] 本地模式显示步骤表格
- [ ] 全局模式显示 AI 回答卡片
- [ ] Debug 模式显示 timing 明细
- [ ] 结果卡片显示模式标签
- [ ] 调试面板显示模式信息
- [ ] 所有修改已提交