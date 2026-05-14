import { useState, useEffect, useRef } from 'react'
import { queryApi, batteryApi, sequenceApi } from '../api/client'
import type { QueryTrace, DisassemblyStep, ParallelBatch } from '../types'
import { GanttChart } from '../components/GanttChart'
import { SequenceSection } from '../components/SequenceSection'

const REASONING_STEPS = [
  { id: 'rewrite', label: '查询重写' },
  { id: 'retrieve', label: '知识检索' },
  { id: 'generate', label: 'LLM生成' },
  { id: 'feedback', label: '反馈优化' },
  { id: 'complete', label: '完成' },
]

interface ProgressState {
  currentStep: number
  status: 'idle' | 'processing' | 'success' | 'error'
  message: string
  timing?: {
    rewrite_ms?: number
    retrieve_ms?: number
    generate_ms?: number
    feedback_ms?: number
    total_ms?: number
  }
}

function ProgressBar({ progress }: { progress: ProgressState }) {
  const percentage = Math.round((progress.currentStep / (REASONING_STEPS.length - 1)) * 100)

  const getStepDetails = () => {
    if (!progress.timing) return null
    const { rewrite_ms, retrieve_ms, generate_ms, feedback_ms } = progress.timing
    return (
      <div style={{ marginTop: '16px', padding: '12px', backgroundColor: '#f8fafc', borderRadius: '8px', fontSize: '13px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', textAlign: 'center' }}>
          <div>
            <div style={{ color: '#666', marginBottom: '4px' }}>查询重写</div>
            <div style={{ fontWeight: 'bold', color: '#3b82f6' }}>{rewrite_ms ? `${rewrite_ms}ms` : '-'}</div>
          </div>
          <div>
            <div style={{ color: '#666', marginBottom: '4px' }}>知识检索</div>
            <div style={{ fontWeight: 'bold', color: '#22c55e' }}>{retrieve_ms ? `${retrieve_ms}ms` : '-'}</div>
          </div>
          <div>
            <div style={{ color: '#666', marginBottom: '4px' }}>LLM生成</div>
            <div style={{ fontWeight: 'bold', color: '#f97316' }}>{generate_ms ? `${generate_ms}ms` : '-'}</div>
          </div>
          <div>
            <div style={{ color: '#666', marginBottom: '4px' }}>反馈优化</div>
            <div style={{ fontWeight: 'bold', color: '#8b5cf6' }}>{feedback_ms ? `${feedback_ms}ms` : '-'}</div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={{ marginTop: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '14px', color: '#666' }}>
        <span>{progress.message || '等待开始...'}</span>
        <span>{percentage}%</span>
      </div>
      <div style={{ height: '10px', backgroundColor: '#e5e7eb', borderRadius: '5px', overflow: 'hidden' }}>
        <div
          style={{
            height: '100%',
            width: `${percentage}%`,
            backgroundColor: progress.status === 'error' ? '#ef4444' : progress.status === 'success' ? '#22c55e' : '#3b82f6',
            transition: 'width 0.5s ease',
          }}
        />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '12px' }}>
        {REASONING_STEPS.map((step, index) => (
          <div
            key={step.id}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              flex: 1,
              opacity: index <= progress.currentStep ? 1 : 0.4,
            }}
          >
            <div
              style={{
                width: '28px',
                height: '28px',
                borderRadius: '50%',
                backgroundColor: index < progress.currentStep ? '#22c55e' : index === progress.currentStep ? '#3b82f6' : '#e5e7eb',
                color: 'white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '12px',
                fontWeight: 'bold',
              }}
            >
              {index < progress.currentStep ? '✓' : index + 1}
            </div>
            <span style={{ fontSize: '11px', marginTop: '4px', textAlign: 'center', color: index === progress.currentStep ? '#3b82f6' : '#666' }}>
              {step.label}
            </span>
          </div>
        ))}
      </div>
      {progress.currentStep > 0 && progress.currentStep < 5 && getStepDetails()}
    </div>
  )
}

export function SequencePlanner() {
  const [batteryModel, setBatteryModel] = useState('')
  const [batteryModels, setBatteryModels] = useState<Array<{ model: string; L1_components: number; L2_entities: number; L3_terms: number }>>([])
  const [showDropdown, setShowDropdown] = useState(false)
  const [loading, setLoading] = useState(false)
  const [topoResult, setTopoResult] = useState<any | null>(null)
  const [llmResult, setLlmResult] = useState<{
    steps?: DisassemblyStep[]
    parallel_batches?: ParallelBatch[]
    trace?: QueryTrace
  } | null>(null)
  const [debug, setDebug] = useState(false)
  const [progress, setProgress] = useState<ProgressState>({
    currentStep: 0,
    status: 'idle',
    message: '',
  })
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
    setTopoResult(null)
    setLlmResult(null)

    try {
      // Call sequence API (topological sort) and plan API (LLM) in parallel
      const [topoRes, llmRes] = await Promise.all([
        sequenceApi.getSequence(batteryModel),
        queryApi.ask({
          battery_model: batteryModel,
          context: [],
          debug,
        })
      ])

      setTopoResult(topoRes)
      setLlmResult(llmRes.data.data)

      // 将 LLM 的拆卸时间合并到拓扑排序序列中
      if (topoRes && topoRes.data && topoRes.data.steps && llmRes.data.data && llmRes.data.data.steps) {
        const llmSteps = llmRes.data.data.steps
        const llmTimeMap = new Map<string, number>()
        for (const step of llmSteps) {
          const name = step.component_name || step.component || ''
          if (name) llmTimeMap.set(name, step.time_seconds)
        }
        for (const step of topoRes.data.steps) {
          const name = step.component_name || step.component || ''
          if (llmTimeMap.has(name)) {
            step.time_seconds = llmTimeMap.get(name)
          }
        }
      }

      setProgress({
        currentStep: 5,
        status: 'success',
        message: '推理完成！',
      })
    } catch (error) {
      console.error('Query failed:', error)
      setProgress(prev => ({ ...prev, status: 'error', message: '推理失败' }))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="page-header">拆卸序列规划</h1>

      <div className="card">
        <div style={{ marginBottom: '20px' }} ref={dropdownRef}>
          <label style={{ display: 'block', marginBottom: '10px', fontWeight: 'bold' }}>
            电池型号
          </label>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
            <div style={{ position: 'relative', flex: 1 }}>
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
            <label style={{ display: 'flex', alignItems: 'center', gap: '5px', padding: '10px 0' }}>
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

      {topoResult || llmResult ? (
        <div>
          {topoResult && topoResult.data && topoResult.data.steps && topoResult.data.steps.length > 0 && (
            <SequenceSection
              title="拓扑排序序列"
              subtitle="确定性 · 基于 precedence 规则"
              badge="topo"
              steps={topoResult.data.steps}
              showReasoningChain={false}
            />
          )}

          {llmResult && llmResult.steps && llmResult.steps.length > 0 && (
            <SequenceSection
              title="LLM 生成序列"
              subtitle="推理链 · 置信度评估"
              badge="llm"
              steps={llmResult.steps}
              showReasoningChain={true}
            />
          )}

          {llmResult && llmResult.steps && llmResult.steps.length > 0 && (
            <GanttChart
              steps={llmResult.steps}
              parallelBatches={llmResult.parallel_batches || []}
            />
          )}

          {debug && llmResult?.trace && (
            <div className="card" style={{ marginTop: '20px' }}>
              <h3>调试信息</h3>
              <div style={{ backgroundColor: '#f5f5f5', padding: '15px', borderRadius: '8px', fontSize: '13px', fontFamily: 'monospace' }}>
                <p><strong>重写查询:</strong> {Array.isArray(llmResult.trace.rewritten_queries) ? llmResult.trace.rewritten_queries.join(', ') : '-'}</p>
                <p><strong>检索节点数:</strong> {llmResult.trace.retrieval_nodes || '-'}</p>
                <p><strong>总组件数:</strong> {llmResult.trace.all_components_count || '-'}</p>
                <p><strong>总关系数:</strong> {llmResult.trace.all_relations_count || '-'}</p>
                {llmResult.trace.timing && (
                  <>
                    <p><strong>查询重写:</strong> {llmResult.trace.timing.rewrite_ms}ms</p>
                    <p><strong>检索:</strong> {llmResult.trace.timing.retrieve_ms}ms</p>
                    <p><strong>生成:</strong> {llmResult.trace.timing.generate_ms}ms</p>
                    <p><strong>反馈:</strong> {llmResult.trace.timing.feedback_ms}ms</p>
                    <p><strong>总计:</strong> {llmResult.trace.timing.total_ms}ms</p>
                  </>
                )}
                {llmResult.trace.iteration_count !== undefined && (
                  <p><strong>迭代次数:</strong> {llmResult.trace.iteration_count}</p>
                )}
              </div>
            </div>
          )}
        </div>
      ) : null}

      {progress.status === 'idle' && !topoResult && !llmResult && !loading && (
        <div className="card" style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
          输入电池型号并点击"生成序列"开始规划
        </div>
      )}

      {(loading || progress.status !== 'idle') && progress.status !== 'success' && <ProgressBar progress={progress} />}

      {progress.status === 'success' && (
        <div className="card" style={{ marginTop: '20px', padding: '15px', backgroundColor: '#d4edda', borderRadius: '8px', textAlign: 'center' }}>
          <span style={{ color: '#155724', fontWeight: 'bold' }}>{progress.message}</span>
          {progress.timing && (
            <span style={{ color: '#155724', marginLeft: '15px' }}>
              总耗时: {progress.timing.total_ms || 0}ms
            </span>
          )}
        </div>
      )}
    </div>
  )
}