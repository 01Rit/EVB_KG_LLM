// frontend/src/components/StepCard.tsx
import { useState } from 'react'
import { DisassemblyStep } from '../types'
import { ReasoningChainPanel } from './ReasoningChainPanel'

interface StepCardProps {
  step: DisassemblyStep
  showReasoningChain?: boolean
  parallelLabel?: string
}

function getGradeLabel(grade: string): string {
  switch (grade) {
    case 'PASS': return '✓ 通过'
    case 'WARN_CONSISTENCY': return '⚠ 一致性警告'
    case 'FAIL_DEPTH': return '✗ 深度不足'
    case 'FAIL_COVERAGE': return '✗ 证据不足'
    default: return grade || ''
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

export function StepCard({ step, showReasoningChain = false, parallelLabel = '' }: StepCardProps) {
  const [isReasoningExpanded, setIsReasoningExpanded] = useState(false)

  const assigneeColor = step.assignee === 'robot' ? '#8b5cf6' : '#10b981'
  const assigneeLabel = step.assignee === 'robot' ? '🤖 机器人' : '👤 人工'

  return (
    <div style={{
      display: 'flex',
      alignItems: 'flex-start',
      gap: '15px',
      padding: '15px',
      backgroundColor: '#fafafa',
      borderRadius: '8px',
      border: '1px solid #eee',
    }}>
      <div style={{
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
      }}>
        {step.id}
      </div>

      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>
          {step.component_name || step.component}
          {parallelLabel && (
            <span style={{ fontWeight: 'normal', color: '#7c3aed', marginLeft: '8px', fontSize: '13px' }}>
              {parallelLabel}
            </span>
          )}
        </div>
        <div style={{ color: '#666', fontSize: '14px', marginBottom: '8px' }}>
          {step.action}
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', fontSize: '13px' }}>
          <span style={{ color: '#888' }}>⏱ {step.time_seconds}s</span>
          <span style={{ color: assigneeColor }}>{assigneeLabel}</span>
          {step.as_score !== undefined && (
            <span style={{
              padding: '2px 8px',
              borderRadius: '4px',
              backgroundColor: '#fee2e2',
              color: '#dc2626',
            }}>
              AS: {step.as_score.toFixed(3)}
            </span>
          )}
          {showReasoningChain && step.confidence !== undefined && (
            <span style={{ color: '#22c55e' }}>
              置信度: {(step.confidence * 100).toFixed(0)}%
            </span>
          )}
          {showReasoningChain && step.confidence_info && (
            <span style={{
              padding: '2px 6px',
              borderRadius: '4px',
              fontSize: '11px',
              fontWeight: 600,
              backgroundColor: getGradeColor(step.confidence_info.grade) + '20',
              color: getGradeColor(step.confidence_info.grade)
            }}>
              {getGradeLabel(step.confidence_info.grade)}
            </span>
          )}
        </div>

        {showReasoningChain && (
          <>
            <button
              onClick={() => setIsReasoningExpanded(!isReasoningExpanded)}
              style={{
                marginTop: '10px',
                padding: '6px 12px',
                backgroundColor: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '13px',
              }}
            >
              {isReasoningExpanded ? '收起推理链' : '查看推理链'}
            </button>

            {isReasoningExpanded && step.reasoning_chain && (
              <div style={{ marginTop: '12px' }}>
                <ReasoningChainPanel
                  reasoningTraces={[]}
                  totalIterations={0}
                  finalConfidence={step.confidence || 0}
                  stepReasoningChain={step.reasoning_chain}
                  stepConfidenceInfo={step.confidence_info}
                />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}