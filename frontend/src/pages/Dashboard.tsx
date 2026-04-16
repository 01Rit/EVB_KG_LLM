import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { importApi } from '../api/client'

interface Stats {
  components: number
  documents: number
  terms: number
}

export function Dashboard() {
  const [stats, setStats] = useState<Stats>({ components: 0, documents: 0, terms: 0 })
  const [history] = useState<any[]>([])
  const navigate = useNavigate()

  useEffect(() => {
    const loadData = async () => {
      try {
        const status = await importApi.getStatus()
        setStats(status.data)
      } catch (error) {
        console.error('Failed to load stats:', error)
      }
    }
    loadData()
  }, [])

  return (
    <div>
      <h1 className="page-header">仪表盘</h1>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginBottom: '20px' }}>
        <div className="card">
          <h3 style={{ color: '#666', fontSize: '14px' }}>组件数量</h3>
          <p style={{ fontSize: '36px', fontWeight: 'bold', color: '#22c55e' }}>{stats.components}</p>
        </div>
        <div className="card">
          <h3 style={{ color: '#666', fontSize: '14px' }}>文档数量</h3>
          <p style={{ fontSize: '36px', fontWeight: 'bold', color: '#3b82f6' }}>{stats.documents}</p>
        </div>
        <div className="card">
          <h3 style={{ color: '#666', fontSize: '14px' }}>术语数量</h3>
          <p style={{ fontSize: '36px', fontWeight: 'bold', color: '#f97316' }}>{stats.terms}</p>
        </div>
      </div>

      <div className="card">
        <h2 style={{ marginBottom: '20px' }}>最近查询记录</h2>
        {history.length === 0 ? (
          <p style={{ color: '#999' }}>暂无查询记录</p>
        ) : (
          <ul style={{ listStyle: 'none' }}>
            {history.map((item) => (
              <li
                key={item.id}
                onClick={() => navigate('/query', { state: { query: item.query } })}
                style={{
                  padding: '10px',
                  marginBottom: '10px',
                  backgroundColor: '#f5f5f5',
                  borderRadius: '8px',
                  cursor: 'pointer',
                }}
              >
                <strong>{item.battery_model}</strong> - {item.query}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="card">
        <h2 style={{ marginBottom: '20px' }}>快速入口</h2>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => navigate('/query')}
            style={{
              padding: '15px 30px',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '16px',
            }}
          >
            新建推理查询
          </button>
          <button
            onClick={() => navigate('/import')}
            style={{
              padding: '15px 30px',
              backgroundColor: '#22c55e',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '16px',
            }}
          >
            导入数据
          </button>
          <button
            onClick={() => navigate('/graph')}
            style={{
              padding: '15px 30px',
              backgroundColor: '#f97316',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '16px',
            }}
          >
            查看图谱
          </button>
        </div>
      </div>
    </div>
  )
}