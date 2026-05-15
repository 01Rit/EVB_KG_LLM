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

  return (
    <div className="card flex gap-lg" style={{
      flexDirection: 'row',
      alignItems: 'flex-start',
      padding: 'var(--space-lg)',
      background: 'var(--color-bg)',
      border: '1px solid var(--color-border)',
    }}>
      {/* Step Number */}
      <div className="flex-shrink-0" style={{
        width: 40, height: 40, borderRadius: '50%',
        background: 'var(--color-accent)', color: 'white',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontWeight: 700, fontSize: 16,
      }}>
        {step.id}
      </div>

      {/* Content */}
      <div className="flex-1">
        {/* Title Row */}
        <div className="flex items-center gap-md mb-sm flex-wrap">
          <span className="font-bold">{step.component_name || step.component}</span>
          {parallelLabel && (
            <span className="badge badge-purple text-xs">{parallelLabel}</span>
          )}
        </div>

        {/* Action */}
        <div className="text-sm text-secondary mb-md">{step.action}</div>

        {/* Metadata */}
        <div className="flex gap-md flex-wrap text-sm">
          <span className="text-muted">⏱ {step.time_seconds}s</span>
          <span className="font-bold" style={{ color: step.assignee === 'robot' ? 'var(--color-robot)' : 'var(--color-human)' }}>
            {step.assignee === 'robot' ? '🤖 机器人' : '👤 人工'}
          </span>
          {step.as_score !== undefined && (
            <span className="badge badge-red">AS: {step.as_score.toFixed(3)}</span>
          )}
          {showReasoningChain && step.confidence !== undefined && (
            <span style={{ color: 'var(--color-l1)' }}>
              置信度: {(step.confidence * 100).toFixed(0)}%
            </span>
          )}
          {showReasoningChain && step.confidence_info && (
            <span className="badge" style={{
              background: getGradeColor(step.confidence_info.grade) + '20',
              color: getGradeColor(step.confidence_info.grade),
            }}>
              {getGradeLabel(step.confidence_info.grade)}
            </span>
          )}
        </div>

        {/* Reasoning Chain Toggle */}
        {showReasoningChain && (
          <>
            <button
              className="btn btn-primary btn-sm mt-md"
              onClick={() => setIsReasoningExpanded(!isReasoningExpanded)}
            >
              {isReasoningExpanded ? '收起推理链' : '查看推理链'}
            </button>
            {isReasoningExpanded && step.reasoning_chain && (
              <div className="mt-md">
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
