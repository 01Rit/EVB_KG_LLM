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

function ProgressBar({ progress, loading }: { progress: ProgressState; loading?: boolean }) {
  const percentage = Math.round((progress.currentStep / (REASONING_STEPS.length - 1)) * 100)

  const getStepDetails = () => {
    if (!progress.timing) return null
    const { rewrite_ms, retrieve_ms, generate_ms, feedback_ms } = progress.timing
    return (
      <div className="mt-lg" style={{ background: 'var(--color-bg)', borderRadius: 'var(--radius-lg)', padding: 'var(--space-md)', fontSize: 13 }}>
        <div className="grid-4 text-center">
          <div>
            <div className="text-xs text-muted mb-sm">查询重写</div>
            <div className="font-bold" style={{ color: 'var(--color-l2)' }}>{rewrite_ms ? `${rewrite_ms}ms` : '-'}</div>
          </div>
          <div>
            <div className="text-xs text-muted mb-sm">知识检索</div>
            <div className="font-bold" style={{ color: 'var(--color-l1)' }}>{retrieve_ms ? `${retrieve_ms}ms` : '-'}</div>
          </div>
          <div>
            <div className="text-xs text-muted mb-sm">LLM生成</div>
            <div className="font-bold" style={{ color: 'var(--color-l3)' }}>{generate_ms ? `${generate_ms}ms` : '-'}</div>
          </div>
          <div>
            <div className="text-xs text-muted mb-sm">反馈优化</div>
            <div className="font-bold" style={{ color: 'var(--color-robot)' }}>{feedback_ms ? `${feedback_ms}ms` : '-'}</div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="progress-steps mb-lg">
        {REASONING_STEPS.map((step, index) => {
          const isCompleted = index < progress.currentStep
          const isCurrent = index === progress.currentStep
          return (
            <div key={step.id} className="progress-step">
              <div className={`progress-step-dot ${isCompleted ? 'completed' : isCurrent ? 'active' : 'pending'}`}>
                {isCompleted ? '✓' : index + 1}
              </div>
              <span className={`progress-step-label ${isCompleted ? 'completed' : isCurrent ? 'active' : 'pending'}`}>
                {step.label}
              </span>
            </div>
          )
        })}
      </div>
      <div className="progress-bar-container">
        <div className="progress-bar-info">
          <span>{progress.message || '等待开始...'}</span>
          <span>{percentage}%</span>
        </div>
        <div className="progress-bar-track">
          <div
            className={`progress-bar-fill ${loading && progress.currentStep === 0 ? 'indeterminate blue' : progress.status === 'error' ? 'error' : progress.status === 'success' ? 'green' : 'blue'}`}
            style={loading && progress.currentStep === 0 ? undefined : { width: `${percentage}%` }}
          />
        </div>
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
  const [llmResult, setLlmResult] = useState<{ steps?: DisassemblyStep[]; parallel_batches?: ParallelBatch[]; trace?: QueryTrace } | null>(null)
  const [debug, setDebug] = useState(false)
  const [progress, setProgress] = useState<ProgressState>({ currentStep: 0, status: 'idle', message: '' })
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const loadBatteryModels = async () => {
      try {
        const res = await batteryApi.search('')
        if (res.data.code === 0) setBatteryModels(res.data.data)
      } catch (err) { console.error('Failed to load battery models:', err) }
    }
    loadBatteryModels()
  }, [])

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) setShowDropdown(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleBatterySearch = async (query: string) => {
    setBatteryModel(query)
    try {
      const res = await batteryApi.search(query)
      if (res.data.code === 0) { setBatteryModels(res.data.data); setShowDropdown(true) }
    } catch (err) { console.error('Failed to search battery models:', err) }
  }

  const handleQuery = async () => {
    if (!batteryModel.trim()) return
    setLoading(true)
    setTopoResult(null)
    setLlmResult(null)

    try {
      const [topoRes, llmRes] = await Promise.all([
        sequenceApi.getSequence(batteryModel),
        queryApi.ask({ battery_model: batteryModel, debug })
      ])

      setTopoResult(topoRes)
      setLlmResult(llmRes.data.data)

      // Merge LLM time estimates into topo steps
      if (topoRes?.data?.steps && llmRes.data.data?.steps) {
        const llmTimeMap = new Map<string, number>()
        for (const step of llmRes.data.data.steps) {
          const name = step.component_name || step.component || ''
          if (name) llmTimeMap.set(name, step.time_seconds)
        }
        for (const step of topoRes.data.steps) {
          const name = step.component_name || step.component || ''
          if (llmTimeMap.has(name)) step.time_seconds = llmTimeMap.get(name)
        }
      }

      // Calculate gantt positions from parallel_groups
      if (topoRes?.data?.steps && topoRes.data.parallel_groups) {
        const keyToStep = new Map<string, any>()
        topoRes.data.steps.forEach((step: any) => {
          if (step.component) keyToStep.set(step.component, step)
          if (step.component_name && step.component_name !== step.component) keyToStep.set(step.component_name, step)
        })
        let cumulativeTime = 0
        topoRes.data.parallel_groups.forEach((group: string[]) => {
          const groupSteps = group.map((key: string) => keyToStep.get(key)).filter(Boolean)
          const groupMaxTime = Math.max(...groupSteps.map((s: any) => s.time_seconds || 0), 0)
          groupSteps.forEach((step: any) => { step.start_time = cumulativeTime; step.duration = step.time_seconds })
          cumulativeTime += groupMaxTime
        })
      }

      setProgress({ currentStep: 5, status: 'success', message: '推理完成！' })
    } catch (error) {
      console.error('Query failed:', error)
      setProgress(prev => ({ ...prev, status: 'error', message: '推理失败' }))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-content">
      <h1 className="page-header">⚡ 拆卸序列规划</h1>

      {/* Input Card */}
      <div className="card mb-xl">
        <div ref={dropdownRef} style={{ position: 'relative' }}>
          <label className="form-label">电池型号</label>
          <div className="flex gap-md items-center">
            <div style={{ flex: 1, position: 'relative' }}>
              <input
                type="text"
                className="form-input"
                value={batteryModel}
                onChange={(e) => handleBatterySearch(e.target.value)}
                onFocus={() => setShowDropdown(true)}
                placeholder="搜索或选择电池型号..."
              />
              {showDropdown && batteryModels.length > 0 && (
                <div className="dropdown">
                  {batteryModels.map((item) => (
                    <div
                      key={item.model}
                      className="dropdown-item"
                      onClick={() => {
                        setBatteryModel(item.model)
                        setShowDropdown(false)
                      }}
                    >
                      <div className="font-bold text-sm">{item.model}</div>
                      <div className="text-xs text-muted">L1: {item.L1_components} | L2: {item.L2_entities} | L3: {item.L3_terms}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <label className="flex items-center gap-sm" style={{ cursor: 'pointer', whiteSpace: 'nowrap' }}>
              <input type="checkbox" checked={debug} onChange={(e) => setDebug(e.target.checked)} style={{ width: 16, height: 16 }} />
              <span className="text-sm">Debug</span>
            </label>
            <button className="btn btn-primary btn-lg" onClick={handleQuery} disabled={loading || !batteryModel.trim()}>
              {loading ? '⏳ 生成中...' : '⚡ 生成序列'}
            </button>
          </div>
        </div>
      </div>

      {/* Results */}
      {topoResult || llmResult ? (
        <div>
          {topoResult?.data?.steps?.length > 0 && (
            <>
              <SequenceSection title="拓扑排序序列" subtitle="确定性 · 基于 precedence 规则" badge="topo" steps={topoResult.data.steps} showReasoningChain={false} parallelGroups={topoResult.data.parallel_groups} />
              <GanttChart steps={topoResult.data.steps} parallelBatches={[]} />
            </>
          )}
          {llmResult && llmResult.steps && llmResult.steps.length > 0 && (
            <>
              <SequenceSection title="LLM 生成序列" subtitle="推理链 · 置信度评估" badge="llm" steps={llmResult.steps} showReasoningChain={true} parallelGroups={llmResult.parallel_batches?.map(batch => batch.tasks.map(taskId => { const s = llmResult!.steps?.find(st => st.id === taskId); return s?.component || s?.component_name || String(taskId) }))} />
              <GanttChart steps={llmResult.steps} parallelBatches={llmResult.parallel_batches || []} />
            </>
          )}
          {debug && llmResult?.trace && (
            <div className="card mt-xl">
              <div className="card-header"><span className="card-title">🐛 调试信息</span></div>
              <div className="font-mono text-sm" style={{ background: 'var(--color-bg)', padding: 'var(--space-lg)', borderRadius: 'var(--radius-lg)' }}>
                <div className="flex-col gap-sm">
                  <div><span className="text-muted">重写查询:</span> {Array.isArray(llmResult.trace.rewritten_queries) ? llmResult.trace.rewritten_queries.join(', ') : '-'}</div>
                  <div><span className="text-muted">检索节点数:</span> {llmResult.trace.retrieval_nodes || '-'}</div>
                  <div><span className="text-muted">总组件数:</span> {llmResult.trace.all_components_count || '-'}</div>
                  <div><span className="text-muted">总关系数:</span> {llmResult.trace.all_relations_count || '-'}</div>
                  {llmResult.trace.timing && (
                    <>
                      <div className="flex gap-xl mt-sm" style={{ borderTop: '1px solid var(--color-border)', paddingTop: 'var(--space-sm)' }}>
                        {[
                          { label: '查询重写', ms: llmResult.trace.timing.rewrite_ms, color: 'var(--color-l2)' },
                          { label: '检索', ms: llmResult.trace.timing.retrieve_ms, color: 'var(--color-l1)' },
                          { label: '生成', ms: llmResult.trace.timing.generate_ms, color: 'var(--color-l3)' },
                          { label: '反馈', ms: llmResult.trace.timing.feedback_ms, color: 'var(--color-robot)' },
                          { label: '总计', ms: llmResult.trace.timing.total_ms, color: 'var(--color-accent)' },
                        ].map(t => (
                          <div key={t.label} className="text-center">
                            <div className="text-xs text-muted">{t.label}</div>
                            <div className="font-bold" style={{ color: t.color }}>{t.ms}ms</div>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                  {llmResult.trace.iteration_count !== undefined && (
                    <div><span className="text-muted">迭代次数:</span> {llmResult.trace.iteration_count}</div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      ) : null}

      {progress.status === 'idle' && !topoResult && !llmResult && !loading && (
        <div className="card" style={{ textAlign: 'center', padding: 'var(--space-4xl)' }}>
          <div className="empty-state">
            <div className="empty-state-icon">⚡</div>
            <div className="empty-state-text">输入电池型号并点击"生成序列"开始规划</div>
          </div>
        </div>
      )}

      {(loading || (progress.status !== 'idle' && progress.status !== 'success')) && (
        <div className="card mb-xl">
          <div className="card-header">
            <span className="card-title">⏳ 序列生成进度</span>
          </div>
          <ProgressBar progress={progress} loading={loading} />
        </div>
      )}

      {progress.status === 'success' && (
        <div className="card mt-xl" style={{ background: 'var(--color-success-bg)', textAlign: 'center' }}>
          <span className="font-bold" style={{ color: '#155724' }}>{progress.message}</span>
          {progress.timing && (
            <span className="text-sm ml-lg" style={{ color: '#155724' }}>
              总耗时: {progress.timing.total_ms || 0}ms
            </span>
          )}
        </div>
      )}
    </div>
  )
}
