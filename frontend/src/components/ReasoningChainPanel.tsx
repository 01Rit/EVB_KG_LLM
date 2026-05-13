import { ReasoningTrace } from '../types'

interface ReasoningChainPanelProps {
  reasoningTraces: ReasoningTrace[]
  totalIterations: number
  finalConfidence: number
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

function DepthBadge({ depth }: { depth: number }) {
  const labels = ['L1', 'L1→L2', 'L1→L2→L3']
  return (
    <span style={{
      background: depth === 0 ? '#dbeafe' : depth === 1 ? '#fef3c7' : '#fce7f3',
      color: depth === 0 ? '#1d4ed8' : depth === 1 ? '#92400e' : '#9d174d',
      padding: '2px 6px',
      borderRadius: '4px',
      fontSize: '11px',
      fontWeight: 600
    }}>
      {labels[depth] || `Depth ${depth}`}
    </span>
  )
}

function ConfidenceBar({ value }: { value: number }) {
  const color = value >= 0.8 ? '#22c55e' : value >= 0.6 ? '#f59e0b' : '#ef4444'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <div style={{
        flex: 1,
        height: '6px',
        background: '#e5e7eb',
        borderRadius: '3px',
        overflow: 'hidden'
      }}>
        <div style={{
          width: `${value * 100}%`,
          height: '100%',
          background: color,
          transition: 'width 0.3s'
        }} />
      </div>
      <span style={{ fontSize: '12px', fontWeight: 600, color, minWidth: '36px' }}>
        {value.toFixed(2)}
      </span>
    </div>
  )
}

export function ReasoningChainPanel({
  reasoningTraces,
  totalIterations,
  finalConfidence
}: ReasoningChainPanelProps) {
  if (!reasoningTraces || reasoningTraces.length === 0) {
    return (
      <div style={{
        padding: '20px',
        textAlign: 'center',
        color: '#6b7280',
        fontSize: '13px'
      }}>
        暂无推理链数据
      </div>
    )
  }

  return (
    <div style={{ padding: '16px', fontSize: '13px' }}>
      {/* 汇总信息 */}
      <div style={{
        display: 'flex',
        gap: '24px',
        padding: '12px 16px',
        background: '#f9fafb',
        borderRadius: '8px',
        marginBottom: '16px'
      }}>
        <div>
          <div style={{ color: '#6b7280', fontSize: '11px', marginBottom: '4px' }}>迭代次数</div>
          <div style={{ fontWeight: 700, fontSize: '18px' }}>{totalIterations}</div>
        </div>
        <div>
          <div style={{ color: '#6b7280', fontSize: '11px', marginBottom: '4px' }}>最终置信度</div>
          <ConfidenceBar value={finalConfidence} />
        </div>
      </div>

      {/* 迭代详情 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {reasoningTraces.map((trace, idx) => {
          const cr = trace.confidence_result
          return (
            <div key={idx} style={{
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              overflow: 'hidden'
            }}>
              {/* 迭代头部 */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '10px 14px',
                background: '#f3f4f6',
                borderBottom: '1px solid #e5e7eb'
              }}>
                <span style={{ fontWeight: 700, color: '#374151' }}>
                  迭代 {trace.iteration + 1}
                </span>
                <DepthBadge depth={trace.target_depth} />
                <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {cr && (
                    <span style={{
                      color: getGradeColor(cr.grade),
                      fontSize: '12px',
                      fontWeight: 600
                    }}>
                      {getGradeLabel(cr.grade)}
                    </span>
                  )}
                  <ConfidenceBar value={trace.confidence} />
                </div>
              </div>

              {/* 节点统计 */}
              <div style={{
                display: 'flex',
                gap: '16px',
                padding: '8px 14px',
                borderBottom: '1px solid #e5e7eb'
              }}>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <span style={{ color: '#6b7280' }}>检索节点:</span>
                  <span style={{ fontWeight: 600 }}>
                    {trace.retrieved_nodes_count}
                    {trace.cross_layer_expansion && (
                      <span style={{ color: '#9ca3af', fontSize: '11px', marginLeft: '4px' }}>
                        (L1:{trace.cross_layer_expansion.l1_nodes || 0},
                         L2:{trace.cross_layer_expansion.l2_nodes || 0},
                         L3:{trace.cross_layer_expansion.l3_nodes || 0})
                      </span>
                    )}
                  </span>
                </div>
                {trace.web_results_count > 0 && (
                  <span style={{ color: '#3b82f6' }}>
                    🌐 联网:{trace.web_results_count}
                  </span>
                )}
              </div>

              {/* 置信度因子 */}
              {cr && (
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(3, 1fr)',
                  gap: '8px',
                  padding: '8px 14px',
                  borderBottom: '1px solid #e5e7eb',
                  background: '#fafafa'
                }}>
                  <div>
                    <div style={{ fontSize: '10px', color: '#9ca3af' }}>evidence_coverage</div>
                    <div style={{ fontWeight: 600, fontSize: '12px' }}>{cr.evidence_coverage.toFixed(2)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '10px', color: '#9ca3af' }}>cross_layer_depth</div>
                    <div style={{ fontWeight: 600, fontSize: '12px' }}>{cr.cross_layer_depth_score.toFixed(2)}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '10px', color: '#9ca3af' }}>consistency</div>
                    <div style={{ fontWeight: 600, fontSize: '12px' }}>{cr.consistency.toFixed(2)}</div>
                  </div>
                </div>
              )}

              {/* 缺失证据 */}
              {trace.missing_evidence && trace.missing_evidence.length > 0 && (
                <div style={{ padding: '8px 14px' }}>
                  <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '4px' }}>仍缺失:</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                    {trace.missing_evidence.map((item, i) => (
                      <span key={i} style={{
                        background: '#fee2e2',
                        color: '#dc2626',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        fontSize: '11px'
                      }}>
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* 推理步骤 */}
              {trace.reasoning_steps && trace.reasoning_steps.length > 0 && (
                <div style={{ padding: '8px 14px' }}>
                  {trace.reasoning_steps.map((step, i) => (
                    <div key={i} style={{
                      fontSize: '12px',
                      color: '#4b5563',
                      marginBottom: '2px'
                    }}>
                      {step}
                    </div>
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
