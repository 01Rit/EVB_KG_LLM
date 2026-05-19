import { useState } from 'react'

interface SourceData {
  type: string
  name: string
  snippet?: string
  url?: string
}

interface CollapsibleSourceProps {
  source: SourceData
  defaultCollapsed?: boolean
}

export function CollapsibleSource({ source, defaultCollapsed = true }: CollapsibleSourceProps) {
  const [isExpanded, setIsExpanded] = useState(!defaultCollapsed)

  return (
    <div className="card" style={{
      padding: 0,
      overflow: 'hidden',
      borderLeft: '3px solid var(--color-accent)',
    }}>
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-md"
        style={{
          padding: '8px 12px',
          cursor: 'pointer',
          userSelect: 'none',
        }}
      >
        <span className="text-xs text-muted" style={{
          transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
          transition: 'transform 0.2s',
        }}>
          ▶
        </span>
        <span className="text-sm" style={{ color: 'var(--color-text-primary)' }}>
          来源：{source.type}: {source.name}
        </span>
      </div>
      {isExpanded && source.snippet && (
        <div className="text-sm" style={{
          padding: '8px 12px',
          borderTop: '1px solid var(--color-border)',
          color: 'var(--color-text-secondary)',
        }}>
          {source.snippet}
          {source.url && (
            <div style={{ marginTop: 8 }}>
              <a href={source.url} target="_blank" rel="noopener noreferrer"
                 style={{ color: '#1677ff', textDecoration: 'underline' }}>
                查看原文 ↗
              </a>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
