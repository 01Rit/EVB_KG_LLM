import { useState, useEffect, useRef } from 'react'
import { batteryApi } from '../api/client'

const CONTEXT_OPTIONS = [
  '室温环境',
  '低湿度',
  '开阔空间',
  '专业工具齐全',
]

const PROGRESS_STAGES = [
  { key: 'understanding', label: '理解问题' },
  { key: 'retrieving_local', label: '检索本地知识库' },
  { key: 'retrieving_web', label: '检索网络资源' },
  { key: 'ranking', label: '排序证据' },
  { key: 'generating', label: '生成回答' },
  { key: 'done', label: '完成' },
]

export function QueryPage() {
  const [batteryModel, setBatteryModel] = useState('')
  const [batteryModels, setBatteryModels] = useState<Array<{ model: string; L1_components: number; L2_entities: number; L3_terms: number }>>([])
  const [showDropdown, setShowDropdown] = useState(false)
  const [context, setContext] = useState<string[]>([])
  const [debug, setDebug] = useState(false)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [sources, setSources] = useState<Array<{ type: string; name: string }>>([])
  const [useWebSearch, setUseWebSearch] = useState(false)
  const [progress, setProgress] = useState<{ stage: string; progress: number; message: string } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const loadBatteryModels = async () => {
      try {
        const res = await batteryApi.search('')
        if (res.data.code === 0) {
          setBatteryModels(res.data.data)
        }
      } catch (err) {
        console.error('Failed to load battery models:', err)
      }
    }
    loadBatteryModels()
  }, [])

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleBatterySearch = async (query: string) => {
    setBatteryModel(query)
    try {
      const res = await batteryApi.search(query)
      if (res.data.code === 0) {
        setBatteryModels(res.data.data)
        setShowDropdown(true)
      }
    } catch (err) {
      console.error('Failed to search battery models:', err)
    }
  }

  const selectBatteryModel = (model: string) => {
    setBatteryModel(model)
    setShowDropdown(false)
  }

  const handleQuery = async () => {
    if (!batteryModel.trim()) return

    setLoading(true)
    setResult(null)
    setSources([])
    setProgress(null)
    setError(null)

    try {
      const response = await fetch('/api/v1/query/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: `${batteryModel}电池相关信息`,
          use_web_search: useWebSearch,
          context,
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('No response body')
      }

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
              } else {
                setProgress({
                  stage: data.stage,
                  progress: data.progress,
                  message: data.message,
                })
              }
            } catch (e) {
              console.error('Failed to parse SSE data:', e)
            }
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

  const currentStageIndex = progress
    ? PROGRESS_STAGES.findIndex(s => s.key === progress.stage)
    : -1

  return (
    <div>
      <h1 className="page-header">知识问答</h1>

      <div className="card">
        <div style={{ marginBottom: '20px' }} ref={dropdownRef}>
          <label style={{ display: 'block', marginBottom: '10px', fontWeight: 'bold' }}>
            电池型号（可选）
          </label>
          <div style={{ position: 'relative' }}>
            <input
              type="text"
              value={batteryModel}
              onChange={(e) => handleBatterySearch(e.target.value)}
              onFocus={() => setShowDropdown(true)}
              placeholder="搜索或选择电池型号..."
              style={{
                width: '100%',
                padding: '10px',
                borderRadius: '8px',
                border: '1px solid #ddd',
                fontSize: '16px',
              }}
            />
            {showDropdown && batteryModels.length > 0 && (
              <div style={{
                position: 'absolute',
                top: '100%',
                left: 0,
                right: 0,
                background: 'white',
                border: '1px solid #ddd',
                borderRadius: '8px',
                marginTop: '4px',
                maxHeight: '200px',
                overflowY: 'auto',
                zIndex: 1000,
                boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
              }}>
                {batteryModels.map((item) => (
                  <div
                    key={item.model}
                    onClick={() => selectBatteryModel(item.model)}
                    style={{
                      padding: '10px',
                      cursor: 'pointer',
                      borderBottom: '1px solid #eee',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = '#f5f5f5')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'white')}
                  >
                    <div style={{ fontWeight: 500 }}>{item.model}</div>
                    <div style={{ fontSize: '12px', color: '#666' }}>
                      L1: {item.L1_components} | L2: {item.L2_entities} | L3: {item.L3_terms}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '10px', fontWeight: 'bold' }}>
            查询模式
          </label>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={() => setUseWebSearch(false)}
              style={{
                padding: '10px 20px',
                backgroundColor: !useWebSearch ? '#3b82f6' : '#fff',
                color: !useWebSearch ? '#fff' : '#333',
                border: '1px solid #ddd',
                borderRadius: '8px',
                cursor: 'pointer',
              }}
            >
              本地知识库
            </button>
            <button
              onClick={() => setUseWebSearch(true)}
              style={{
                padding: '10px 20px',
                backgroundColor: useWebSearch ? '#3b82f6' : '#fff',
                color: useWebSearch ? '#fff' : '#333',
                border: '1px solid #ddd',
                borderRadius: '8px',
                cursor: 'pointer',
              }}
            >
              本地+联网
            </button>
          </div>
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '10px', fontWeight: 'bold' }}>
            工作环境（可多选）
          </label>
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            {CONTEXT_OPTIONS.map(option => (
              <label key={option} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <input
                  type="checkbox"
                  checked={context.includes(option)}
                  onChange={() => {
                    setContext(prev =>
                      prev.includes(option)
                        ? prev.filter(c => c !== option)
                        : [...prev, option]
                    )
                  }}
                />
                {option}
              </label>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <input
              type="checkbox"
              checked={debug}
              onChange={(e) => setDebug(e.target.checked)}
            />
            <span>Debug模式</span>
          </label>
        </div>

        <button
          onClick={handleQuery}
          disabled={loading}
          style={{
            padding: '15px 30px',
            backgroundColor: loading ? '#ccc' : '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: '16px',
          }}
        >
          {loading ? '查询中...' : '开始查询'}
        </button>
      </div>

      {loading && progress && (
        <div className="card">
          <h3>查询进度</h3>
          <div style={{ marginBottom: '20px' }}>
            {PROGRESS_STAGES.map((stage, index) => {
              const isCompleted = index < currentStageIndex
              const isCurrent = index === currentStageIndex
              const isPending = index > currentStageIndex

              return (
                <div
                  key={stage.key}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    marginBottom: '8px',
                    opacity: isPending ? 0.5 : 1,
                  }}
                >
                  <div style={{
                    width: '24px',
                    height: '24px',
                    borderRadius: '50%',
                    backgroundColor: isCompleted ? '#22c55e' : isCurrent ? '#3b82f6' : '#ddd',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white',
                    fontSize: '12px',
                    fontWeight: 'bold',
                  }}>
                    {isCompleted ? '✓' : index + 1}
                  </div>
                  <span style={{
                    color: isCurrent ? '#3b82f6' : 'inherit',
                    fontWeight: isCurrent ? 'bold' : 'normal',
                  }}>
                    {stage.label}
                  </span>
                  {isCurrent && progress.message && (
                    <span style={{ color: '#666', fontSize: '14px' }}>
                      - {progress.message}
                    </span>
                  )}
                </div>
              )
            })}
          </div>
          <div style={{
            width: '100%',
            height: '8px',
            backgroundColor: '#eee',
            borderRadius: '4px',
            overflow: 'hidden',
          }}>
            <div style={{
              width: `${(progress.progress || 0) * 100}%`,
              height: '100%',
              backgroundColor: '#3b82f6',
              transition: 'width 0.3s ease',
            }} />
          </div>
        </div>
      )}

      {error && (
        <div className="card" style={{ backgroundColor: '#fef2f2', borderLeft: '4px solid #ef4444' }}>
          <h3 style={{ color: '#dc2626' }}>错误</h3>
          <p>{error}</p>
        </div>
      )}

      {result && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h2>回答</h2>
            <span style={{
              padding: '4px 12px',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: 'bold',
              background: useWebSearch ? '#f0fdf4' : '#e0f2fe',
              color: useWebSearch ? '#15803d' : '#0369a1',
            }}>
              {useWebSearch ? '本地+联网' : '本地知识库'}
            </span>
          </div>

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

          {sources.length > 0 && (
            <div style={{ marginBottom: '20px' }}>
              <h4 style={{ marginBottom: '10px' }}>参考来源</h4>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {sources.map((source, i) => (
                  <span
                    key={i}
                    style={{
                      padding: '4px 12px',
                      backgroundColor: '#f5f5f5',
                      borderRadius: '4px',
                      fontSize: '14px',
                    }}
                  >
                    {source.type}: {source.name}
                  </span>
                ))}
              </div>
            </div>
          )}

          <button
            onClick={() => {
              const blob = new Blob([result], { type: 'text/plain' })
              const url = URL.createObjectURL(blob)
              const a = document.createElement('a')
              a.href = url
              a.download = `answer_${batteryModel || 'query'}.txt`
              a.click()
            }}
            style={{
              padding: '10px 20px',
              backgroundColor: '#22c55e',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
            }}
          >
            导出回答
          </button>
        </div>
      )}
    </div>
  )
}