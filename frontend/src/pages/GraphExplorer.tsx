import { useState, useEffect, useCallback } from 'react'
import { graphApi } from '../api/client'
import { GraphView } from '../components/GraphView/GraphView'
import type { GraphNode } from '../types'

export function GraphExplorer() {
  const [nodes, setNodes] = useState<GraphNode[]>([])
  const [edges, setEdges] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<string>('all')
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)

  const loadGraph = useCallback(async () => {
    setLoading(true)
    try {
      const [nodesRes, edgesRes] = await Promise.all([
        graphApi.getNodes(),
        graphApi.getRelationships(),
      ])
      setNodes(nodesRes.data)
      setEdges(edgesRes.data)
    } catch (error) {
      console.error('Failed to load graph:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadGraph()
  }, [loadGraph])

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      loadGraph()
      return
    }
    setLoading(true)
    try {
      const res = await graphApi.search(searchQuery)
      setNodes(res.data)
      setEdges([])
    } catch (error) {
      console.error('Search failed:', error)
    } finally {
      setLoading(false)
    }
  }

  const filteredNodes = filterType === 'all'
    ? nodes
    : nodes.filter(n => n.type === filterType)

  return (
    <div className="page-content">
      <h1 className="page-header">🕸️ 图谱浏览</h1>

      <div className="card">
        {/* Toolbar */}
        <div className="flex gap-md mb-lg flex-wrap">
          <div style={{ flex: 1, minWidth: 200 }}>
            <input
              type="text"
              className="form-input"
              placeholder="搜索节点..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
          </div>
          <button className="btn btn-primary" onClick={handleSearch}>
            🔍 搜索
          </button>
          <select
            className="form-select"
            style={{ width: 'auto', minWidth: 130 }}
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
          >
            <option value="all">全部类型</option>
            <option value="L1">L1 组件</option>
            <option value="L2">L2 文档</option>
            <option value="L3">L3 术语</option>
          </select>
          <button className="btn btn-ghost" onClick={loadGraph}>
            🔄 刷新
          </button>
        </div>

        {/* Graph + Detail Panel */}
        <div className="flex gap-xl" style={{ minHeight: 500 }}>
          {/* Graph Area */}
          <div className="flex-1" style={{
            background: 'var(--color-bg)',
            borderRadius: 'var(--radius-lg)',
            overflow: 'hidden',
            position: 'relative',
            border: '1px solid var(--color-border)',
          }}>
            {loading ? (
              <div className="empty-state" style={{ paddingTop: 200 }}>
                <div className="skeleton" style={{ width: 300, height: 24, margin: '0 auto 12px' }} />
                <div className="skeleton" style={{ width: 200, height: 16, margin: '0 auto' }} />
              </div>
            ) : (
              <GraphView
                nodes={filteredNodes}
                edges={edges}
                onNodeClick={setSelectedNode}
              />
            )}
          </div>

          {/* Node Detail Panel */}
          {selectedNode && (
            <div className="card" style={{
              width: 280,
              flexShrink: 0,
              alignSelf: 'flex-start',
              position: 'sticky',
              top: 24,
            }}>
              <div className="flex items-center justify-between mb-lg">
                <span className="card-title">📌 节点详情</span>
                <button
                  className="btn btn-ghost btn-sm"
                  onClick={() => setSelectedNode(null)}
                >
                  ✕
                </button>
              </div>

              <div className="flex-col gap-md">
                <div>
                  <div className="text-xs text-muted mb-sm">ID</div>
                  <div className="text-sm font-mono">{selectedNode.id}</div>
                </div>
                <div>
                  <div className="text-xs text-muted mb-sm">名称</div>
                  <div className="text-sm font-bold">{selectedNode.name}</div>
                </div>
                <div>
                  <div className="text-xs text-muted mb-sm">类型</div>
                  <span className={`badge ${
                    selectedNode.type === 'L1' ? 'badge-green' :
                    selectedNode.type === 'L2' ? 'badge-blue' :
                    selectedNode.type === 'L3' ? 'badge-amber' : 'badge-gray'
                  }`}>
                    {selectedNode.type}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Layer Legend */}
        <div className="flex gap-xl mt-lg flex-wrap">
          <div className="flex items-center gap-sm">
            <div style={{ width: 12, height: 12, background: 'var(--color-l1)', borderRadius: 3 }} />
            <span className="text-sm text-secondary">L1 组件</span>
            <span className="text-xs text-muted">
              ({nodes.filter(n => n.type === 'L1').length})
            </span>
          </div>
          <div className="flex items-center gap-sm">
            <div style={{ width: 12, height: 12, background: 'var(--color-l2)', borderRadius: 3 }} />
            <span className="text-sm text-secondary">L2 文档</span>
            <span className="text-xs text-muted">
              ({nodes.filter(n => n.type === 'L2').length})
            </span>
          </div>
          <div className="flex items-center gap-sm">
            <div style={{ width: 12, height: 12, background: 'var(--color-l3)', borderRadius: 3 }} />
            <span className="text-sm text-secondary">L3 术语</span>
            <span className="text-xs text-muted">
              ({nodes.filter(n => n.type === 'L3').length})
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
