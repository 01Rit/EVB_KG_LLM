import { useEffect, useRef } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import type { GraphNode, GraphEdge } from '../../types'

interface GraphViewProps {
  nodes: GraphNode[]
  edges: GraphEdge[]
  onNodeClick?: (node: GraphNode) => void
}

const NODE_COLORS = {
  L1: '#22c55e',
  L2: '#3b82f6',
  L3: '#f97316',
}

export function GraphView({ nodes, edges, onNodeClick }: GraphViewProps) {
  const graphRef = useRef<any>(null)

  const graphData = {
    nodes: nodes.map(n => ({
      ...n,
      color: NODE_COLORS[n.type as keyof typeof NODE_COLORS] || '#999',
    })),
    links: edges.map(e => ({
      source: e.from_,
      target: e.to,
    })),
  }

  useEffect(() => {
    if (graphRef.current) {
      graphRef.current.d3Force('charge').strength(-100)
    }
  }, [])

  return (
    <ForceGraph2D
      ref={graphRef}
      graphData={graphData}
      nodeLabel="name"
      nodeColor="color"
      linkColor={() => '#999'}
      linkWidth={1}
      onNodeClick={(node: any) => onNodeClick?.(node as GraphNode)}
    />
  )
}
