import { DisassemblyStep, ParallelBatch } from '../types'

interface GanttChartProps {
  steps: DisassemblyStep[]
  parallelBatches?: ParallelBatch[]
}

function getGradeLabel(grade: string): string {
  switch (grade) {
    case 'PASS': return '✓ 通过'
    case 'WARN_CONSISTENCY': return '⚠ 一致性警告'
    case 'FAIL_DEPTH': return '✗ 深度不足'
    case 'FAIL_COVERAGE': return '✗ 证据不足'
    default: return grade || '未知'
  }
}

export function GanttChart({ steps, parallelBatches = [] }: GanttChartProps) {
  if (!steps || steps.length === 0) {
    return (
      <div className="gantt-container">
        <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
          No steps data available
        </div>
      </div>
    )
  }

  // Build stepId -> batch mapping
    const stepToBatch = new Map<number, ParallelBatch>()
    parallelBatches.forEach(batch => {
      if (batch.tasks) {
        batch.tasks.forEach(taskId => {
          stepToBatch.set(taskId, batch)
        })
      }
    })

    // Calculate total time in minutes
    const totalTimeMinutes = parallelBatches.length > 0
      ? Math.max(...parallelBatches.map(b => b.start_time + b.duration)) / 60
      : Math.max(...steps.map(s => (s.start_time || 0) + (s.time_seconds || 0)), 1) / 60

    // Time axis markers in minutes
    const timeMarkers = [0, 1, 2, 3, 4, 5, 6].map(i => ({
      percent: (i / 6) * 100,
      label: Math.round((i / 6) * totalTimeMinutes)
    }))

  return (
    <div>
      {/* 图例 */}
      <div className="gantt-legend" style={{ display: 'flex', gap: '20px', marginBottom: '10px', fontSize: '13px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ width: '16px', height: '16px', background: '#4C72B0', borderRadius: '3px' }}></div>
          <span>人工拆卸</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ width: '16px', height: '16px', background: '#DD8452', borderRadius: '3px' }}></div>
          <span>机器人拆卸</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ width: '16px', height: '16px', background: '#9d174d', borderRadius: '3px' }}></div>
          <span>★ L3 跨层</span>
        </div>
      </div>

      {/* 甘特图主体 */}
      <div className="gantt-container">
        {/* 时间轴 - 使用百分比定位 */}
        <div className="gantt-header">
          <div className="gantt-label-col"></div>
          <div className="gantt-time-axis" style={{ position: 'relative' }}>
            {timeMarkers.map(marker => (
              <div
                key={marker.percent}
                className="time-marker"
                style={{
                  position: 'absolute',
                  left: `${marker.percent}%`,
                  transform: 'translateX(-50%)'
                }}
              >
                {marker.label}min
              </div>
            ))}
          </div>
        </div>

        {/* 任务行 - 每行一个任务 */}
        <div className="gantt-body">
          {steps.map((step) => {
            const startTimeSeconds = step.start_time || 0
            const durationSeconds = step.duration || step.time_seconds || 0
            const startTimeMinutes = startTimeSeconds / 60
            const durationMinutes = durationSeconds / 60
            const leftPercent = (startTimeMinutes / totalTimeMinutes) * 100
            const widthPercent = (durationMinutes / totalTimeMinutes) * 100
            const stepName = step.component_name || step.component

            // 跨层深度判断：reasoning_chain 中是否有 L3 证据
            const hasL3 = step.reasoning_chain?.links?.some(l => l.evidence_layer === 3)
            const ci = step.confidence_info

            // 构建 tooltip 内容
            const tooltipContent = buildTooltipContent(step, durationMinutes, hasL3, ci)

            return (
              <div key={step.id} className="gantt-row">
                <div className="gantt-label" title={stepName}>
                  {stepName}
                </div>
                <div className="gantt-bar-container" style={{ position: 'relative' }}>
                  <div
                    className={`gantt-bar ${step.assignee === 'robot' ? 'robot' : 'human'}`}
                    style={{
                      position: 'absolute',
                      left: `${leftPercent}%`,
                      width: `${Math.max(widthPercent, 2)}%`
                    }}
                    data-tooltip={tooltipContent}
                  >
                    {durationMinutes.toFixed(2)}m
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* 全局 tooltip 样式 */}
      <style>{`
        .gantt-bar[data-tooltip] {
          position: relative;
          cursor: pointer;
        }
        .gantt-bar[data-tooltip]:hover::after {
          content: attr(data-tooltip);
          position: absolute;
          bottom: calc(100% + 8px);
          left: 50%;
          transform: translateX(-50%);
          background: rgba(17, 24, 39, 0.95);
          color: #f9fafb;
          padding: 10px 14px;
          border-radius: 8px;
          font-size: 12px;
          white-space: pre-line;
          z-index: 100;
          min-width: 220px;
          max-width: 320px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.3);
          line-height: 1.5;
        }
      `}</style>
    </div>
  )
}

function buildTooltipContent(
  step: DisassemblyStep,
  durationMinutes: number,
  hasL3: boolean | undefined,
  ci: DisassemblyStep['confidence_info']
): string {
  const parts: string[] = []

  parts.push(`${step.component_name || step.component}`)
  parts.push(`时长: ${durationMinutes.toFixed(2)}min`)

  if (step.tool) {
    const tools = Array.isArray(step.tool) ? step.tool.join(', ') : step.tool
    parts.push(`工具: ${tools}`)
  }

  if (step.safety_level) {
    parts.push(`安全等级: ${step.safety_level}`)
  }

  if (ci) {
    parts.push(`置信度: ${ci.overall.toFixed(2)} (${getGradeLabel(ci.grade)})`)
    parts.push(`  coverage: ${ci.evidence_coverage.toFixed(2)}`)
    parts.push(`  depth: ${ci.cross_layer_depth_score.toFixed(2)}`)
    parts.push(`  consistency: ${ci.consistency.toFixed(2)}`)
  } else if (step.confidence !== undefined) {
    parts.push(`置信度: ${step.confidence.toFixed(2)}`)
  }

  if (hasL3) {
    parts.push(`★ 跨层深度: L1→L2→L3`)
  }

  if (step.reasoning_chain?.overall_reasoning) {
    parts.push(`---`)
    parts.push(step.reasoning_chain.overall_reasoning.slice(0, 100))
    if (step.reasoning_chain.overall_reasoning.length > 100) {
      parts.push(`...`)
    }
  }

  return parts.join('\n')
}