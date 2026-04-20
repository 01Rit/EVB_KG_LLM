import { DisassemblyStep, ParallelBatch } from '../types'

interface GanttChartProps {
  steps: DisassemblyStep[]
  parallelBatches?: ParallelBatch[]
}

export function GanttChart({ steps, parallelBatches }: GanttChartProps) {
  if (!parallelBatches || parallelBatches.length === 0) {
    return (
      <div className="gantt-container">
        <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
          No parallel batch data available
        </div>
      </div>
    )
  }

  const totalTime = Math.max(...parallelBatches.map(b => b.start_time + b.duration), 1)

  const stepMap = new Map(steps.map(s => [s.id, s]))

  const timeMarkers: number[] = []
  const interval = Math.ceil(totalTime / 6)
  for (let t = 0; t <= totalTime; t += interval) {
    timeMarkers.push(t)
  }

  return (
    <div>
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
          {parallelBatches.map(batch => {
            const widthPercent = (batch.duration / totalTime) * 100

            return (
              <div key={batch.batch_id} className="gantt-row">
                <div className="gantt-label">
                  Batch {batch.batch_id}
                </div>
                <div className="gantt-bar-container" style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                  {batch.tasks.map(taskId => {
                    const step = stepMap.get(taskId)
                    if (!step) return null
                    return (
                      <div
                        key={taskId}
                        className={`gantt-bar ${step.assignee === 'robot' ? 'robot' : 'human'}`}
                        style={{
                          width: `${Math.max(widthPercent, 2)}%`
                        }}
                        title={`${step.component_name || step.component} (${step.time_seconds}s)`}
                      >
                        {step.component_name || step.component}
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}