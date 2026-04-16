import { useState } from 'react'
import { queryApi } from '../api/client'
import type { QueryResponse, DisassemblyStep } from '../types'

export function SequencePlanner() {
  const [batteryModel, setBatteryModel] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<QueryResponse | null>(null)
  const [debug, setDebug] = useState(false)

  const handleQuery = async () => {
    if (!batteryModel.trim()) return

    setLoading(true)
    try {
      const res = await queryApi.ask({
        battery_model: batteryModel,
        context: [],
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

  const getSafetyColor = (level: number) => {
    if (level >= 4) return '#dc2626'
    if (level >= 3) return '#f59e0b'
    if (level >= 2) return '#3b82f6'
    return '#22c55e'
  }

  return (
    <div>
      <h1 className="page-header">拆卸序列规划</h1>

      <div className="card">
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '10px', fontWeight: 'bold' }}>
            电池型号
          </label>
          <div style={{ display: 'flex', gap: '10px' }}>
            <input
              type="text"
              value={batteryModel}
              onChange={(e) => setBatteryModel(e.target.value)}
              placeholder="例如: Tesla_Model_3"
              style={{
                flex: 1,
                padding: '10px',
                borderRadius: '8px',
                border: '1px solid #ddd',
                fontSize: '16px',
              }}
            />
            <label style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <input
                type="checkbox"
                checked={debug}
                onChange={(e) => setDebug(e.target.checked)}
              />
              <span>Debug</span>
            </label>
            <button
              onClick={handleQuery}
              disabled={loading || !batteryModel.trim()}
              style={{
                padding: '10px 20px',
                backgroundColor: loading ? '#ccc' : '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: '16px',
              }}
            >
              {loading ? '生成中...' : '生成序列'}
            </button>
          </div>
        </div>
      </div>

      {result && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h2>拆卸序列 ({steps.length} 步)</h2>
            <span style={{ color: '#666' }}>模式: {result.data?.mode || 'local'}</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {steps.map((step, idx) => (
              <div
                key={step.id || idx}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '15px',
                  padding: '15px',
                  backgroundColor: '#fafafa',
                  borderRadius: '8px',
                  border: '1px solid #eee',
                }}
              >
                <div
                  style={{
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
                  }}
                >
                  {step.id || idx + 1}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>
                    {step.component}
                  </div>
                  <div style={{ color: '#666', fontSize: '14px' }}>
                    {step.action}
                  </div>
                  {step.tool && step.tool.length > 0 && (
                    <div style={{ marginTop: '5px', fontSize: '13px', color: '#888' }}>
                      工具: {step.tool.join(', ')}
                    </div>
                  )}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '5px' }}>
                  {step.confidence !== undefined && (
                    <span style={{ fontSize: '13px', color: '#22c55e' }}>
                      置信度: {(step.confidence * 100).toFixed(0)}%
                    </span>
                  )}
                  {step.safety_level !== undefined && (
                    <span
                      style={{
                        fontSize: '12px',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        backgroundColor: getSafetyColor(step.safety_level),
                        color: 'white',
                      }}
                    >
                      安全等级: {step.safety_level}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>

          {debug && result.data?.trace && (
            <div style={{ marginTop: '20px' }}>
              <h3>调试信息</h3>
              <div style={{ backgroundColor: '#f5f5f5', padding: '15px', borderRadius: '8px', fontSize: '13px', fontFamily: 'monospace' }}>
                <p><strong>重写查询:</strong> {result.data.trace.rewritten_queries?.join(', ') || '-'}</p>
                <p><strong>检索节点数:</strong> {result.data.trace.retrieval_nodes || '-'}</p>
                <p><strong>总组件数:</strong> {result.data.trace.all_components_count || '-'}</p>
                <p><strong>总关系数:</strong> {result.data.trace.all_relations_count || '-'}</p>
                {result.data.trace.timing && (
                  <>
                    <p><strong>查询重写:</strong> {result.data.trace.timing.rewrite_ms}ms</p>
                    <p><strong>检索:</strong> {result.data.trace.timing.retrieve_ms}ms</p>
                    <p><strong>生成:</strong> {result.data.trace.timing.generate_ms}ms</p>
                    <p><strong>反馈:</strong> {result.data.trace.timing.feedback_ms}ms</p>
                    <p><strong>总计:</strong> {result.data.trace.timing.total_ms}ms</p>
                  </>
                )}
                {result.data.trace.iteration_count !== undefined && (
                  <p><strong>迭代次数:</strong> {result.data.trace.iteration_count}</p>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {!result && !loading && (
        <div className="card" style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
          输入电池型号并点击"生成序列"开始规划
        </div>
      )}
    </div>
  )
}