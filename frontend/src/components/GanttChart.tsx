import { DisassemblyStep } from '../types'

interface GanttChartProps {
  steps: DisassemblyStep[]
}

export function GanttChart({ steps }: GanttChartProps) {
  if (!steps || steps.length === 0) {
    return (
      <div className="gantt-container">
        <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
          No steps data available
        </div>
      </div>
    )
  }

  // 计算总时间
  const totalTime = Math.max(...steps.map(s => (s.start_time || 0) + (s.time_seconds || 0)), 1)

  // 时间轴刻度（百分比对应）
  const timeMarkers = [0, 1, 2, 3, 4, 5, 6].map(i => ({
    percent: (i / 6) * 100,
    label: Math.round((i / 6) * totalTime)
  }))

  return (
    <div>
      {/* 图例 */}
      <div className="gantt-legend" style={{ display: 'flex', gap: '20px', marginBottom: '10px', fontSize: '13px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ width: '16px', height: '16px', background: '#6b7280', borderRadius: '3px' }}></div>
          <span>人工拆卸</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ width: '16px', height: '16px', background: '#2563eb', borderRadius: '3px' }}></div>
          <span>机器人拆卸</span>
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
                {marker.label}s
              </div>
            ))}
          </div>
        </div>

        {/* 任务行 - 每行一个任务 */}
        <div className="gantt-body">
          {steps.map((step) => {
            const startTime = step.start_time || 0
            const duration = step.time_seconds || 0
            const leftPercent = (startTime / totalTime) * 100
            const widthPercent = (duration / totalTime) * 100
            const stepName = step.component_name || step.component

            return (
              <div key={step.id} className="gantt-row">
                <div className="gantt-label" title={stepName}>
                  {stepName}
                </div>
                <div className="gantt-bar-container" style={{ position: 'relative' }}>
                  <div
                    className={`gantt-bar ${step.assignee === 'robot' ? 'robot' : 'human'} `}
                    style={{
                      position: 'absolute',
                      left: `${leftPercent}%`,
                      width: `${Math.max(widthPercent, 2)}%`
                    }}
                    title={`${stepName} (${duration}s)`}
                  >
                    {duration}s
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}