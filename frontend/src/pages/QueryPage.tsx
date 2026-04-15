import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import { queryApi } from '../api/client'
import type { QueryResponse, DisassemblyStep } from '../types'

const CONTEXT_OPTIONS = [
  '室温环境',
  '低湿度',
  '开阔空间',
  '专业工具齐全',
]

export function QueryPage() {
  const location = useLocation()

  const [batteryModel, setBatteryModel] = useState('')
  const [context, setContext] = useState<string[]>([])
  const [debug, setDebug] = useState(false)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<QueryResponse | null>(null)

  const handleContextToggle = (option: string) => {
    setContext(prev =>
      prev.includes(option)
        ? prev.filter(c => c !== option)
        : [...prev, option]
    )
  }

  const handleQuery = async () => {
    if (!batteryModel.trim()) return

    setLoading(true)
    try {
      const res = await queryApi.ask({
        battery_model: batteryModel,
        context,
        debug,
      })
      setResult(res.data)
    } catch (error) {
      console.error('Query failed:', error)
    } finally {
      setLoading(false)
    }
  }

  const steps: DisassemblyStep[] = result?.data?.steps || []

  return (
    <div>
      <h1 className="page-header">推理查询</h1>

      <div className="card">
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '10px', fontWeight: 'bold' }}>
            电池型号
          </label>
          <input
            type="text"
            value={batteryModel}
            onChange={(e) => setBatteryModel(e.target.value)}
            placeholder="例如: X123"
            style={{
              width: '100%',
              padding: '10px',
              borderRadius: '8px',
              border: '1px solid #ddd',
              fontSize: '16px',
            }}
          />
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
                  onChange={() => handleContextToggle(option)}
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
            <span>Debug模式（显示推理过程）</span>
          </label>
        </div>

        <button
          onClick={handleQuery}
          disabled={loading || !batteryModel.trim()}
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

      {result && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h2>拆卸方案</h2>
            <button
              onClick={() => {
                const dataStr = JSON.stringify(result, null, 2)
                const blob = new Blob([dataStr], { type: 'application/json' })
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = `disassembly_${batteryModel}.json`
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
              导出结果
            </button>
          </div>

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

          {debug && result.data?.trace && (
            <div>
              <h3>推理过程（Debug）</h3>
              <div style={{ backgroundColor: '#f5f5f5', padding: '15px', borderRadius: '8px', marginTop: '10px' }}>
                <p><strong>重写查询:</strong> {result.data.trace.rewritten_queries?.join(', ')}</p>
                <p><strong>检索路径:</strong> {result.data.trace.retrieval_paths?.join(', ')}</p>
                <p><strong>证据数量:</strong> {result.data.trace.evidence_count}</p>
                <p><strong>迭代次数:</strong> {result.data.trace.iteration_count}</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}