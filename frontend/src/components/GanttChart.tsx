import { DisassemblyStep } from '../types'

interface GanttChartProps {
  steps: DisassemblyStep[]
  totalTimeSeconds: number
}

export function GanttChart({ steps, totalTimeSeconds }: GanttChartProps) {
  const timeMarkers: number[] = []
  if (totalTimeSeconds > 0) {
    const interval = Math.ceil(totalTimeSeconds / 6)
    for (let t = 0; t <= totalTimeSeconds; t += interval) {
      timeMarkers.push(t)
    }
  }

  return (
    <div className="gantt-container">
      <div className="gantt-header">
        <div className="gantt-label-col"></div>
        <div className="gantt-time-axis">
          {timeMarkers.map(t => (
            <div key={t} className="time-marker">{t}s</div>
          ))}
        </div>
      </div>
      <div className="gantt-body">
        {steps.map((step, idx) => (
          <div key={step.id || idx} className="gantt-row">
            <div className="gantt-label" title={step.component_name || step.component}>
              {step.component_name || step.component}
            </div>
            <div className="gantt-bar-container">
              <div
                className={`gantt-bar ${step.assignee === 'robot' ? 'robot' : 'human'}`}
                style={{
                  width: `${totalTimeSeconds > 0 ? ((step.time_seconds || 0) / totalTimeSeconds) * 100 : 0}%`
                }}
              >
                {step.time_seconds}s
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}