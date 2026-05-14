// frontend/src/components/SequenceSection.tsx
import { DisassemblyStep } from '../types'
import { StepCard } from './StepCard'

interface SequenceSectionProps {
  title?: string
  subtitle?: string
  badge: 'topo' | 'llm'
  steps: DisassemblyStep[]
  showReasoningChain: boolean
  parallelGroups?: string[][]
}

export function SequenceSection({
  badge,
  steps,
  showReasoningChain,
  parallelGroups,
}: SequenceSectionProps) {
  // 构建 component -> 同组其他零件 的映射
  const parallelLabelMap = new Map<string, string>()
  if (parallelGroups) {
    parallelGroups.forEach((group, idx) => {
      if (group.length > 1) {
        group.forEach(comp => {
          const others = group.filter(c => c !== comp).join(', ')
          parallelLabelMap.set(comp, `(可并行: ${others})`)
        })
      }
    })
  }

  const badgeStyle = badge === 'topo'
    ? { background: '#dbeafe', color: '#1d4ed8' }
    : { background: '#fef3c7', color: '#92400e' }

  return (
    <div className="card" style={{ marginBottom: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
        <span style={{
          ...badgeStyle,
          padding: '4px 12px',
          borderRadius: '12px',
          fontSize: '14px',
          fontWeight: 600
        }}>
          {badge === 'topo' ? '🔵 拓扑排序' : '🟡 LLM 生成'}
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {steps.map((step, idx) => (
          <StepCard
            key={step.id || idx}
            step={step}
            showReasoningChain={showReasoningChain}
            parallelLabel={parallelLabelMap.get(step.component_name || step.component) || ''}
          />
        ))}
      </div>
    </div>
  )
}
