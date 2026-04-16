# 4.16 迭代前端同步设计

## 概述

将 4.16 迭代的后端 GraphRAG 改进功能（local/global 模式）同步至前端 QueryPage。

## 需求来源

- **4.16 迭代**: Task 9-10 添加了 Planner mode 参数和 API mode 参数
- **Brainstorming**: 2026-04-16 确认了 UI 设计方案

---

## 设计方案

### 1. Mode 切换 UI

采用**标签切换**方式：

```tsx
<div className="mode-tabs">
  <button className={mode === 'local' ? 'active' : ''} onClick={() => setMode('local')}>
    本地检索
  </button>
  <button className={mode === 'global' ? 'active' : ''} onClick={() => setMode('global')}>
    全局查询
  </button>
</div>
```

### 2. 响应格式展示

**本地模式** (`mode: 'local'`)：
- 返回结构：`{ steps: DisassemblyStep[] }`
- 展示：拆卸步骤表格

**全局模式** (`mode: 'global'`)：
- 返回结构：`{ response: string }`
- 展示：AI 回答文本卡片（带"社区摘要"说明）

```tsx
{result?.data?.mode === 'global' ? (
  <div className="ai-response-card">
    <h3>AI 回答</h3>
    <p>{result.data.response}</p>
    <span className="mode-tag">全局查询</span>
  </div>
) : (
  /* 步骤表格 */
)}
```

### 3. 调试信息增强

新增 timing 明细和模式信息：

```tsx
{debug && result.data?.trace && (
  <div className="debug-panel">
    <p><strong>查询模式:</strong> {result.data.mode}</p>
    <p><strong>重写查询:</strong> {result.data.trace.rewritten_queries?.join(', ')}</p>
    <p><strong>检索路径:</strong> {result.data.trace.retrieval_paths?.join(', ')}</p>
    <p><strong>证据数量:</strong> {result.data.trace.evidence_count}</p>
    <p><strong>迭代次数:</strong> {result.data.trace.iteration_count}</p>
    <p><strong>Timing:</strong></p>
    <ul>
      <li>重写: {result.data.trace.timing?.rewrite_ms}ms</li>
      <li>检索: {result.data.trace.timing?.retrieve_ms}ms</li>
      <li>生成: {result.data.trace.timing?.generate_ms}ms</li>
      <li>反馈: {result.data.trace.timing?.feedback_ms}ms</li>
      <li>总计: {result.data.trace.timing?.total_ms}ms</li>
    </ul>
  </div>
)}
```

### 4. Mode 字段显示

**模式标签**（结果卡片左上角）：
```tsx
<span className={`mode-badge ${result?.data?.mode}`}>
  {result?.data?.mode === 'local' ? '本地检索' : '全局查询'}
</span>
```

---

## 界面原型

```
┌─────────────────────────────────────────────────────┐
│ QueryPage                                            │
├─────────────────────────────────────────────────────┤
│ 电池型号: [____________]                              │
│                                                       │
│ [本地检索] [全局查询]  ← 标签切换                     │
│                                                       │
│ 工作环境: ☑ 室温环境  ☑ 低湿度                        │
│                                                       │
│ [☑ Debug模式]  [ 开始查询 ]                          │
├─────────────────────────────────────────────────────┤
│ 拆卸方案                                    [导出]   │
│ ┌──────────────┐                                    │
│ │ 🔵 本地检索   │  ← 模式标签                        │
│ └──────────────┘                                    │
│ ┌─────────────────────────────────────────────────┐ │
│ │ 序号 │ 组件  │ 操作   │ 工具  │ 置信度 │        │
│ │ 1    │ 上壳体│ 拆卸   │ 螺丝刀│ 95%   │        │
│ │ 2    │ 电池芯│ 取出   │ 镊子  │ 90%   │        │
│ └─────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────┤
│ 推理过程（Debug）                                     │
│ 查询模式: local                                      │
│ 重写查询: 拆卸X123电池, X123拆解步骤                  │
│ Timing: 重写 120ms | 检索 450ms | 生成 800ms        │
└─────────────────────────────────────────────────────┘
```

---

## 文件修改清单

| 文件 | 修改内容 |
|------|----------|
| `frontend/src/types/index.ts` | 添加 `mode?: 'local' \| 'global'` 到 QueryResponse.data |
| `frontend/src/api/client.ts` | `queryApi.ask()` 添加 `mode` 参数 |
| `frontend/src/pages/QueryPage.tsx` | 添加标签切换、响应区分、调试增强、模式标签 |

---

## 样式建议

```css
.mode-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.mode-tabs button {
  padding: 10px 20px;
  border: 1px solid #ddd;
  background: #fff;
  cursor: pointer;
}

.mode-tabs button.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.mode-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
}

.mode-badge.local {
  background: #e0f2fe;
  color: #0369a1;
}

.mode-badge.global {
  background: #f0fdf4;
  color: #15803d;
}

.ai-response-card {
  background: #fafafa;
  padding: 20px;
  border-radius: 8px;
  border-left: 4px solid #3b82f6;
}
```

---

## 验收标准

1. ✅ 标签切换可切换 local/global 模式
2. ✅ 本地模式显示步骤表格
3. ✅ 全局模式显示 AI 回答卡片
4. ✅ Debug 模式显示 timing 明细
5. ✅ 结果卡片显示模式标签
6. ✅ 调试面板显示模式信息