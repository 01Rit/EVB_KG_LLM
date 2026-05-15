import { ReasoningTrace, ReasoningLink } from '../types'

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

interface ReasoningChainPanelProps {
  reasoningTraces?: ReasoningTrace[]
  totalIterations?: number
  finalConfidence?: number
  stepReasoningChain?: StepReasoningChain
  stepConfidenceInfo?: ConfidenceInfo
}

function getGradeLabel(grade: string): string {
  switch (grade) {
    case 'PASS': return '✓ 通过'
    case 'WARN_CONSISTENCY': return '⚠ 一致性警告'
    case 'FAIL_DEPTH': return '✗ 深度不足'
    case 'FAIL_COVERAGE': return '✗ 证据不足'
    default: return grade
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

function renderStepReasoningChain(chain: StepReasoningChain, info?: ConfidenceInfo) {
  const gradeColor = info ? getGradeColor(info.grade) : '#6b7280'
  return (
    <div className="card" style={{
      background: '#fffbeb',
      borderColor: '#fde68a',
      padding: 'var(--space-md)',
    }}>
      {info && (
        <div className="mb-md">
          <div className="text-xs text-muted mb-sm">综合置信度</div>
          <div className="flex items-center gap-md">
            <div className="progress-bar-track" style={{ flex: 1, height: 6 }}>
              <div className="progress-bar-fill" style={{ width: `${info.overall * 100}%`, background: gradeColor }} />
            </div>
            <span className="font-bold text-sm" style={{ color: gradeColor, minWidth: 36 }}>
              {info.overall.toFixed(2)}
            </span>
          </div>
        </div>
      )}

      <div className="flex-col gap-sm mb-md">
        {chain.links.map((link, idx) => (
          <div key={idx} className="card" style={{ padding: 'var(--space-md)', background: 'white' }}>
            <div className="flex items-center gap-md mb-sm">
              <span className={`badge ${
                link.evidence_layer === 1 ? 'badge-green' :
                link.evidence_layer === 2 ? 'badge-blue' : 'badge-amber'
              }`}>
                L{link.evidence_layer}
              </span>
              <span className="text-sm" style={{ flex: 1 }}>{link.claim}</span>
              <span className="font-bold text-sm" style={{ color: 'var(--color-l1)' }}>
                {link.confidence.toFixed(2)}
              </span>
            </div>
            <div className="text-xs text-secondary" style={{ background: 'var(--color-bg)', padding: '6px', borderRadius: 'var(--radius-sm)' }}>
              证据: {link.evidence_snippet?.slice(0, 100)}...
            </div>
          </div>
        ))}
      </div>

      {chain.overall_reasoning && (
        <div className="text-sm text-secondary" style={{
          fontStyle: 'italic',
          paddingTop: 'var(--space-sm)',
          borderTop: '1px dashed var(--color-border)',
        }}>
          综合推理：{chain.overall_reasoning}
        </div>
      )}
    </div>
  )
}

function DepthBadge({ depth }: { depth: number }) {
  const labels = ['L1', 'L1→L2', 'L1→L2→L3']
  return (
    <span className={`badge ${
      depth === 0 ? 'badge-blue' : depth === 1 ? 'badge-amber' : 'badge-red'
    }`}>
      {labels[depth] || `Depth ${depth}`}
    </span>
  )
}

function ConfidenceBar({ value }: { value: number }) {
  const color = value >= 0.8 ? '#22c55e' : value >= 0.6 ? '#f59e0b' : '#ef4444'
  return (
    <div className="flex items-center gap-md" style={{ minWidth: 160 }}>
      <div className="progress-bar-track" style={{ flex: 1, height: 6 }}>
        <div className="progress-bar-fill" style={{ width: `${value * 100}%`, background: color }} />
      </div>
      <span className="font-bold text-sm" style={{ color, minWidth: 36 }}>
        {value.toFixed(2)}
      </span>
    </div>
  )
}

export function ReasoningChainPanel({
  reasoningTraces,
  totalIterations,
  finalConfidence,
  stepReasoningChain,
  stepConfidenceInfo,
}: ReasoningChainPanelProps) {
  if (stepReasoningChain) {
    return renderStepReasoningChain(stepReasoningChain, stepConfidenceInfo)
  }

  if (!reasoningTraces || reasoningTraces.length === 0) {
    return (
      <div className="empty-state" style={{ padding: 'var(--space-xl)' }}>
        <div className="empty-state-text text-sm">暂无推理链数据</div>
      </div>
    )
  }

  return (
    <div className="text-sm">
      {/* Summary */}
      <div className="card mb-lg" style={{ background: 'var(--color-bg)', display: 'flex', gap: 24, padding: 'var(--space-md) var(--space-lg)' }}>
        <div>
          <div className="text-xs text-muted mb-xs">迭代次数</div>
          <div className="font-bold" style={{ fontSize: 18 }}>{totalIterations}</div>
        </div>
        <div>
          <div className="text-xs text-muted mb-xs">最终置信度</div>
          <ConfidenceBar value={finalConfidence ?? 0} />
        </div>
      </div>

      {/* Iterations */}
      <div className="flex-col gap-md">
        {reasoningTraces.map((trace, idx) => {
          const cr = trace.confidence_result
          return (
            <div key={idx} className="card" style={{ padding: 0, overflow: 'hidden' }}>
              {/* Header */}
              <div className="flex items-center gap-md" style={{
                padding: '10px 14px',
                background: '#f3f4f6',
                borderBottom: '1px solid var(--color-border)',
              }}>
                <span className="font-bold">迭代 {trace.iteration + 1}</span>
                <DepthBadge depth={trace.target_depth} />
                <div className="flex items-center gap-md" style={{ marginLeft: 'auto' }}>
                  {cr && (
                    <span className="font-bold text-xs" style={{ color: getGradeColor(cr.grade) }}>
                      {getGradeLabel(cr.grade)}
                    </span>
                  )}
                  <ConfidenceBar value={trace.confidence} />
                </div>
              </div>

              {/* Stats */}
              <div className="flex gap-lg" style={{ padding: '8px 14px', borderBottom: '1px solid var(--color-border-light)' }}>
                <span className="text-xs text-secondary">
                  检索节点: <span className="font-bold">{trace.retrieved_nodes_count}</span>
                  {trace.cross_layer_expansion && (
                    <span className="text-muted" style={{ marginLeft: 4 }}>
                      (L1:{trace.cross_layer_expansion.l1_nodes || 0},
                       L2:{trace.cross_layer_expansion.l2_nodes || 0},
                       L3:{trace.cross_layer_expansion.l3_nodes || 0})
                    </span>
                  )}
                </span>
                {trace.web_results_count > 0 && (
                  <span className="text-xs" style={{ color: 'var(--color-accent)' }}>
                    🌐 联网: {trace.web_results_count}
                  </span>
                )}
              </div>

              {/* Confidence Factors */}
              {cr && (
                <div className="grid-3" style={{ padding: '8px 14px', borderBottom: '1px solid var(--color-border-light)', background: '#fafafa' }}>
                  <div>
                    <div className="text-xs text-muted">evidence_coverage</div>
                    <div className="font-bold text-xs">{cr.evidence_coverage.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted">cross_layer_depth</div>
                    <div className="font-bold text-xs">{cr.cross_layer_depth_score.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted">consistency</div>
                    <div className="font-bold text-xs">{cr.consistency.toFixed(2)}</div>
                  </div>
                </div>
              )}

              {/* Missing Evidence */}
              {trace.missing_evidence && trace.missing_evidence.length > 0 && (
                <div style={{ padding: '8px 14px' }}>
                  <div className="text-xs text-muted mb-xs">仍缺失:</div>
                  <div className="flex gap-xs flex-wrap">
                    {trace.missing_evidence.map((item, i) => (
                      <span key={i} className="badge badge-red text-xs">{item}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* Reasoning Steps */}
              {trace.reasoning_steps && trace.reasoning_steps.length > 0 && (
                <div style={{ padding: '8px 14px' }}>
                  {trace.reasoning_steps.map((step, i) => (
                    <div key={i} className="text-xs mb-xs" style={{ color: '#4b5563' }}>{step}</div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
