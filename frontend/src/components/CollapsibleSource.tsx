// frontend/src/components/CollapsibleSource.tsx
import { useState } from 'react'

interface SourceData {
  type: string      // e.g., "本地KG-Component"
  name: string      // e.g., "绝缘体"
  snippet?: string   // 证据片段
}

interface CollapsibleSourceProps {
  source: SourceData
  defaultCollapsed?: boolean
}

export function CollapsibleSource({ source, defaultCollapsed = true }: CollapsibleSourceProps) {
  const [isExpanded, setIsExpanded] = useState(!defaultCollapsed)

  return (
    <div style={{
      backgroundColor: '#f9fafb',
      borderLeft: '3px solid #3b82f6',
      borderRadius: '4px',
      margin: '8px 0',
      overflow: 'hidden'
    }}>
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          padding: '8px 12px',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          userSelect: 'none'
        }}
      >
        <span style={{
          fontSize: '12px',
          color: '#6b7280',
          transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
          transition: 'transform 0.2s'
        }}>
          ▶
        </span>
        <span style={{ fontSize: '13px', color: '#374151' }}>
          来源：{source.type}: {source.name}
        </span>
      </div>
      {isExpanded && source.snippet && (
        <div style={{
          padding: '8px 12px',
          backgroundColor: '#fff',
          borderTop: '1px solid #e5e7eb',
          fontSize: '13px',
          color: '#4b5563'
        }}>
          {source.snippet}
        </div>
      )}
    </div>
  )
}
