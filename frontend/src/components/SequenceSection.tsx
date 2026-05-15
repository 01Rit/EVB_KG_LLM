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
  const idToName = new Map<string, string>()
  steps.forEach(step => {
    const name = step.component_name || step.component
    if (step.component) idToName.set(step.component, name)
    if (step.component_name && step.component_name !== step.component) idToName.set(step.component_name, name)
  })

  const parallelLabelMap = new Map<string, string>()
  if (parallelGroups) {
    parallelGroups.forEach((group) => {
      if (group.length > 1) {
        group.forEach(comp => {
          const others = group.filter(c => c !== comp).map(c => idToName.get(c) || c).join(', ')
          parallelLabelMap.set(comp, `(可并行: ${others})`)
        })
      }
    })
  }

  return (
    <div className="card mb-xl">
      <div className="flex items-center gap-md mb-lg">
        <span className={`badge ${badge === 'topo' ? 'badge-blue' : 'badge-amber'}`}>
          {badge === 'topo' ? '🔵 拓扑排序' : '🟡 LLM 生成'}
        </span>
      </div>

      <div className="flex-col gap-md">
        {steps.map((step, idx) => (
          <StepCard
            key={step.id || idx}
            step={step}
            showReasoningChain={showReasoningChain}
            parallelLabel={parallelLabelMap.get(step.component) || parallelLabelMap.get(step.component_name || '') || ''}
          />
        ))}
      </div>
    </div>
  )
}
