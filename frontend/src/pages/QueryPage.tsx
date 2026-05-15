import { useState, useEffect, useRef } from 'react'
import { MarkdownRenderer } from '../components/MarkdownRenderer'

const PROGRESS_STAGES = [
  { key: 'understanding', label: '理解问题' },
  { key: 'retrieving_local', label: '检索本地知识库' },
  { key: 'retrieving_web', label: '检索网络资源' },
  { key: 'ranking', label: '排序证据' },
  { key: 'generating', label: '生成回答' },
  { key: 'done', label: '完成' },
]

const MAX_HISTORY = 5

export function QueryPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [queryHistory, setQueryHistory] = useState<string[]>([])
  const [showHistory, setShowHistory] = useState(false)
  const [debug, setDebug] = useState(false)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [sources, setSources] = useState<Array<{ type: string; name: string }>>([])
  const [useWebSearch, setUseWebSearch] = useState(false)
  const [progress, setProgress] = useState<{ stage: string; progress: number; message: string } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const historyRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const saved = localStorage.getItem('queryHistory')
    if (saved) {
      try { setQueryHistory(JSON.parse(saved)) } catch (e) { /* ignore */ }
    }
  }, [])

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (historyRef.current && !historyRef.current.contains(event.target as Node)) {
        setShowHistory(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const addToHistory = (query: string, batteryModel?: string) => {
    const trimmed = query.trim()
    if (!trimmed) return
    setQueryHistory(prev => {
      const filtered = prev.filter(q => q !== trimmed)
      const newHistory = [trimmed, ...filtered].slice(0, MAX_HISTORY)
      localStorage.setItem('queryHistory', JSON.stringify(newHistory))
      return newHistory
    })
    // 保存带时间戳的详细历史记录供仪表盘使用
    try {
      const richHistory = JSON.parse(localStorage.getItem('richQueryHistory') || '[]')
      const newEntry = { query: trimmed, battery_model: batteryModel || '', created_at: new Date().toISOString() }
      const filtered = richHistory.filter((h: any) => h.query !== trimmed)
      filtered.unshift(newEntry)
      localStorage.setItem('richQueryHistory', JSON.stringify(filtered.slice(0, MAX_HISTORY)))
    } catch (e) { /* ignore */ }
  }

  const clearHistory = () => {
    setQueryHistory([])
    localStorage.removeItem('queryHistory')
  }

  const handleQuery = async () => {
    const queryText = searchQuery.trim()
    if (!queryText) return

    setLoading(true)
    setResult(null)
    setSources([])
    setProgress(null)
    setError(null)

    try {
      const response = await fetch('/api/v1/query/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: queryText, use_web_search: useWebSearch }),
      })
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`)

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.error) {
                setError(data.error)
                break
              }
              if (data.stage === 'done') {
                setResult(data.answer || '')
                setProgress({ stage: 'done', progress: 1, message: '完成' })
                addToHistory(queryText)
              } else {
                setProgress({ stage: data.stage, progress: data.progress, message: data.message })
              }
            } catch (e) { /* ignore parse errors */ }
          }
        }
      }
    } catch (err) {
      console.error('Query failed:', err)
      setError(err instanceof Error ? err.message : '查询失败')
    } finally {
      setLoading(false)
    }
  }

  const visibleStages = useWebSearch
    ? PROGRESS_STAGES
    : PROGRESS_STAGES.filter(s => s.key !== 'retrieving_web')

  return (
    <div className="page-content">
      <h1 className="page-header">🔍 知识问答</h1>

      {/* Query Input Card */}
      <div className="card mb-xl">
        <div className="mb-lg" ref={historyRef} style={{ position: 'relative' }}>
          <label className="form-label">输入问题</label>
          <div style={{ position: 'relative' }}>
            <input
              ref={inputRef}
              type="text"
              className="form-input"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setShowHistory(true)}
              placeholder="输入您的问题..."
              disabled={loading}
            />
            {showHistory && queryHistory.length > 0 && (
              <div className="dropdown">
                <div className="flex items-center justify-between" style={{ padding: '8px 12px', borderBottom: '1px solid var(--color-border)', background: 'var(--color-bg)' }}>
                  <span className="text-xs text-muted">最近查询</span>
                  <button className="btn btn-ghost btn-sm" onClick={(e) => { e.stopPropagation(); clearHistory() }}>
                    清空
                  </button>
                </div>
                {queryHistory.map((item, index) => (
                  <div
                    key={index}
                    className="dropdown-item"
                    onClick={() => {
                      setSearchQuery(item)
                      setShowHistory(false)
                      inputRef.current?.focus()
                    }}
                  >
                    <span className="text-sm">{item}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="mb-lg">
          <label className="form-label">查询模式</label>
          <div className="flex gap-md">
            <button
              className={`btn ${!useWebSearch ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setUseWebSearch(false)}
            >
              📚 本地知识库
            </button>
            <button
              className={`btn ${useWebSearch ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setUseWebSearch(true)}
            >
              🌐 本地+联网
            </button>
          </div>
        </div>

        <div className="mb-lg">
          <label className="flex items-center gap-md" style={{ cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={debug}
              onChange={(e) => setDebug(e.target.checked)}
              style={{ width: 16, height: 16 }}
            />
            <span className="text-sm">Debug 模式</span>
          </label>
        </div>

        <button
          className="btn btn-primary btn-lg"
          onClick={handleQuery}
          disabled={loading || !searchQuery.trim()}
        >
          {loading ? '⏳ 查询中...' : '🚀 开始查询'}
        </button>
      </div>

      {/* Progress - show immediately on loading */}
      {loading && (
        <div className="card mb-xl">
          <div className="card-header">
            <span className="card-title">⏳ 查询进度</span>
          </div>
          <div className="progress-steps mb-lg">
            {visibleStages.map((stage, index) => {
              const currentIdx = progress ? visibleStages.findIndex(s => s.key === progress.stage) : -1
              const isCompleted = index < currentIdx
              const isCurrent = index === currentIdx
              return (
                <div key={stage.key} className="progress-step">
                  <div className={`progress-step-dot ${isCompleted ? 'completed' : isCurrent ? 'active' : 'pending'}`}>
                    {isCompleted ? '✓' : index + 1}
                  </div>
                  <span className={`progress-step-label ${isCompleted ? 'completed' : isCurrent ? 'active' : 'pending'}`}>
                    {stage.label}
                  </span>
                </div>
              )
            })}
          </div>
          <div className="progress-bar-container">
            <div className="progress-bar-info">
              <span>{progress?.message || '正在准备...'}</span>
              {progress ? <span>{Math.round((progress.progress || 0) * 100)}%</span> : <span>--</span>}
            </div>
            <div className="progress-bar-track">
              <div
                className={`progress-bar-fill ${!progress ? 'indeterminate blue' : 'blue'}`}
                style={progress ? { width: `${(progress.progress || 0) * 100}%` } : undefined}
              />
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="error-card mb-xl">
          <div className="error-card-title">❌ 错误</div>
          <div className="error-card-text">{error}</div>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="card mb-xl">
          <div className="card-header">
            <span className="card-title">💡 回答</span>
            <span className={`badge ${useWebSearch ? 'badge-green' : 'badge-blue'}`}>
              {useWebSearch ? '本地+联网' : '本地知识库'}
            </span>
          </div>
          <div className="mb-lg" style={{
            background: 'var(--color-bg)',
            padding: 'var(--space-xl)',
            borderRadius: 'var(--radius-lg)',
            borderLeft: '4px solid var(--color-accent)',
          }}>
            <MarkdownRenderer content={result} />
          </div>

          {sources.length > 0 && (
            <div className="mb-lg">
              <div className="text-sm font-bold mb-md">参考来源</div>
              <div className="flex gap-sm flex-wrap">
                {sources.map((source, i) => (
                  <span key={i} className="badge badge-gray">
                    {source.type}: {source.name}
                  </span>
                ))}
              </div>
            </div>
          )}

          <button
            className="btn btn-success"
            onClick={() => {
              const blob = new Blob([result], { type: 'text/plain' })
              const url = URL.createObjectURL(blob)
              const a = document.createElement('a')
              a.href = url
              a.download = `answer_${searchQuery || 'query'}.txt`
              a.click()
              URL.revokeObjectURL(url)
            }}
          >
            📥 导出回答
          </button>
        </div>
      )}
    </div>
  )
}
