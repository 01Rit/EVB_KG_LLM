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
    <div>
      <h1 className="page-header">图谱浏览</h1>

      <div className="card">
        <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
          <input
            type="text"
            placeholder="搜索节点..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            style={{
              flex: 1,
              padding: '10px',
              borderRadius: '8px',
              border: '1px solid #ddd',
            }}
          />
          <button onClick={handleSearch} style={{
            padding: '10px 20px',
            backgroundColor: '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
          }}>
            搜索
          </button>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            style={{
              padding: '10px',
              borderRadius: '8px',
              border: '1px solid #ddd',
            }}
          >
            <option value="all">全部</option>
            <option value="L1">L1 组件</option>
            <option value="L2">L2 文档</option>
            <option value="L3">L3 术语</option>
          </select>
          <button onClick={loadGraph} style={{
            padding: '10px 20px',
            backgroundColor: '#666',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
          }}>
            刷新
          </button>
        </div>

        <div style={{ display: 'flex', gap: '20px' }}>
          <div style={{ flex: 1, height: '500px', backgroundColor: '#f0f0f0', borderRadius: '8px' }}>
            {loading ? (
              <div style={{ padding: '20px', textAlign: 'center' }}>加载中...</div>
            ) : (
              <GraphView
                nodes={filteredNodes}
                edges={edges}
                onNodeClick={setSelectedNode}
              />
            )}
          </div>

          {selectedNode && (
            <div style={{ width: '300px', padding: '20px', backgroundColor: '#f9f9f9', borderRadius: '8px' }}>
              <h3>节点详情</h3>
              <p><strong>ID:</strong> {selectedNode.id}</p>
              <p><strong>名称:</strong> {selectedNode.name}</p>
              <p><strong>类型:</strong> {selectedNode.type}</p>
              <button
                onClick={() => setSelectedNode(null)}
                style={{
                  marginTop: '10px',
                  padding: '5px 10px',
                  backgroundColor: '#666',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                }}
              >
                关闭
              </button>
            </div>
          )}
        </div>

        <div style={{ marginTop: '20px', display: 'flex', gap: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <div style={{ width: '12px', height: '12px', backgroundColor: '#22c55e', borderRadius: '2px' }} />
            <span>L1 组件</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <div style={{ width: '12px', height: '12px', backgroundColor: '#3b82f6', borderRadius: '2px' }} />
            <span>L2 文档</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <div style={{ width: '12px', height: '12px', backgroundColor: '#f97316', borderRadius: '2px' }} />
            <span>L3 术语</span>
          </div>
        </div>
      </div>
    </div>
  )
}
