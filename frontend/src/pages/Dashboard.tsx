import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { importApi } from '../api/client'

interface Stats {
  components: number
  documents: number
  terms: number
}

interface QueryRecord {
  id: number
  battery_model: string
  query: string
  created_at?: string
}

const QUICK_ACTIONS = [
  {
    path: '/query',
    label: '推理查询',
    desc: '自然语言查询拆卸知识',
    icon: '🔍',
    color: 'var(--color-l2)',
  },
  {
    path: '/sequence',
    label: '序列规划',
    desc: '智能拆卸顺序编排',
    icon: '⚡',
    color: 'var(--color-l1)',
  },
  {
    path: '/import',
    label: '数据导入',
    desc: '导入组件、文档、术语',
    icon: '📥',
    color: 'var(--color-l3)',
  },
  {
    path: '/graph',
    label: '图谱浏览',
    desc: '可视化知识网络',
    icon: '🕸️',
    color: 'var(--color-robot)',
  },
]

function AnimatedNumber({ value }: { value: number; label: string }) {
  const [display, setDisplay] = useState(0)
  const [animated, setAnimated] = useState(false)

  useEffect(() => {
    if (value === 0) return
    const duration = 800
    const steps = 30
    const increment = value / steps
    let current = 0
    let step = 0

    const timer = setInterval(() => {
      step++
      current = Math.min(Math.round(increment * step), value)
      setDisplay(current)
      if (step >= steps) {
        clearInterval(timer)
        setDisplay(value)
        setAnimated(true)
      }
    }, duration / steps)

    return () => clearInterval(timer)
  }, [value])

  return (
    <span className={`stat-value${animated ? '' : ''}`} style={{ opacity: animated || display > 0 ? 1 : 0.5 }}>
      {display}
    </span>
  )
}

export function Dashboard() {
  const [stats, setStats] = useState<Stats>({ components: 0, documents: 0, terms: 0 })
  const [history, setHistory] = useState<QueryRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const loadData = async () => {
      try {
        const [statusRes] = await Promise.all([
          importApi.getStatus(),
        ])
        setStats(statusRes.data)
        // 从 localStorage 读取查询历史（QueryPage 保存的带时间戳记录）
        try {
          const stored = localStorage.getItem('richQueryHistory')
          if (stored) {
            const parsed = JSON.parse(stored)
            if (Array.isArray(parsed)) setHistory(parsed.slice(0, 5))
          }
        } catch (e) { /* ignore */ }
      } catch (error) {
        console.error('Failed to load stats:', error)
        setError('加载数据失败，请确认后端服务已启动')
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  const total = stats.components + stats.documents + stats.terms
  const layerData = useMemo(() => [
    { label: 'L1 组件', value: stats.components, color: 'var(--color-l1)', bg: 'var(--color-l1-bg)' },
    { label: 'L2 文档和实体', value: stats.documents, color: 'var(--color-l2)', bg: 'var(--color-l2-bg)' },
    { label: 'L3 术语', value: stats.terms, color: 'var(--color-l3)', bg: 'var(--color-l3-bg)' },
  ], [stats])

  return (
    <div className="page-content">
      <h1 className="page-header">📊 仪表盘</h1>

      {/* Stats Cards */}
      <div className="grid-3" style={{ marginBottom: 'var(--space-2xl)' }}>
        <div className="stat-card l1" style={{ animationDelay: '0s' }}>
          <div className="stat-label">
            <span>📦</span> L1 组件数量
          </div>
          {loading ? (
            <div className="skeleton" style={{ height: '36px', width: '80px', marginTop: '8px' }} />
          ) : (
            <AnimatedNumber value={stats.components} label="组件" />
          )}
          <div className="stat-trend" style={{ color: 'var(--color-l1)' }}>
            知识图谱基础节点
          </div>
        </div>

        <div className="stat-card l2" style={{ animationDelay: '0.1s' }}>
          <div className="stat-label">
            <span>📄</span> L2 文档和实体数量
          </div>
          {loading ? (
            <div className="skeleton" style={{ height: '36px', width: '80px', marginTop: '8px' }} />
          ) : (
            <AnimatedNumber value={stats.documents} label="文档" />
          )}
          <div className="stat-trend" style={{ color: 'var(--color-l2)' }}>
            参考文档与实体
          </div>
        </div>

        <div className="stat-card l3" style={{ animationDelay: '0.2s' }}>
          <div className="stat-label">
            <span>📖</span> L3 术语数量
          </div>
          {loading ? (
            <div className="skeleton" style={{ height: '36px', width: '80px', marginTop: '8px' }} />
          ) : (
            <AnimatedNumber value={stats.terms} label="术语" />
          )}
          <div className="stat-trend" style={{ color: 'var(--color-l3)' }}>
            专业术语定义
          </div>
        </div>
      </div>

      {/* Layer Distribution & System Status */}
      <div className="grid-2" style={{ marginBottom: 'var(--space-2xl)' }}>
        {/* Layer Distribution */}
        <div className="card" style={{ animation: 'slideUp 0.4s ease-out 0.1s both' }}>
          <div className="card-header">
            <span className="card-title">📊 三层知识分布</span>
            <span className="card-subtitle">总计 {total} 个节点</span>
          </div>
          <div className="flex-col gap-lg">
            {/* Distribution bar */}
            {total > 0 && (
              <div style={{
                display: 'flex',
                height: '32px',
                borderRadius: 'var(--radius-md)',
                overflow: 'hidden',
              }}>
                {layerData.map(layer => layer.value > 0 && (
                  <div
                    key={layer.label}
                    style={{
                      flex: layer.value,
                      background: layer.color,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'white',
                      fontSize: '12px',
                      fontWeight: 700,
                      minWidth: '40px',
                      transition: 'flex 0.6s ease',
                    }}
                  >
                    {layer.value}
                  </div>
                ))}
              </div>
            )}
            {/* Legend */}
            <div className="flex gap-xl flex-wrap">
              {layerData.map(layer => (
                <div key={layer.label} className="flex items-center gap-sm">
                  <div style={{
                    width: '12px',
                    height: '12px',
                    borderRadius: '3px',
                    background: layer.color,
                    flexShrink: 0,
                  }} />
                  <span className="text-sm text-secondary">{layer.label}</span>
                  <span className="font-bold text-sm">{layer.value}</span>
                  <span className="text-xs text-muted">
                    ({total > 0 ? ((layer.value / total) * 100).toFixed(1) : 0}%)
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* System Status */}
        <div className="card" style={{ animation: 'slideUp 0.4s ease-out 0.2s both' }}>
          <div className="card-header">
            <span className="card-title">⚙️ 系统状态</span>
            <span className={`badge ${loading ? 'badge-gray' : error ? 'badge-red' : 'badge-green'}`}>
              {loading ? '检测中' : error ? '异常' : '运行中'}
            </span>
          </div>
          <div className="flex-col gap-lg">
            <div className="flex items-center justify-between">
              <span className="text-sm text-secondary">知识图谱引擎</span>
              <span className={`badge ${error ? 'badge-red' : 'badge-green'}`}>
                {error ? '连接失败' : '已连接'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-secondary">数据库节点数</span>
              <span className="font-bold text-sm">{total}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-secondary">存储层</span>
              <span className="text-xs font-mono" style={{ color: 'var(--color-text-muted)' }}>
                Neo4j
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Queries */}
      <div className="card" style={{ marginBottom: 'var(--space-2xl)', animation: 'slideUp 0.4s ease-out 0.3s both' }}>
        <div className="card-header">
          <span className="card-title">🕐 最近查询</span>
          {history.length > 0 && (
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => navigate('/query')}
            >
              查看全部
            </button>
          )}
        </div>
        {history.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">🔍</div>
            <div className="empty-state-text">
              暂无查询记录<br />
              <span className="text-xs text-muted">前往推理查询页面开始探索知识图谱</span>
            </div>
          </div>
        ) : (
          <div className="flex-col" style={{ gap: 'var(--space-sm)' }}>
            {history.map((item, i) => (
              <div
                key={item.id || i}
                onClick={() => navigate('/query', { state: { query: item.query } })}
                className="flex items-center justify-between"
                style={{
                  padding: 'var(--space-md) var(--space-lg)',
                  background: 'var(--color-bg)',
                  borderRadius: 'var(--radius-md)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  border: '1px solid transparent',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = 'var(--color-border)'
                  e.currentTarget.style.background = 'var(--color-surface)'
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = 'transparent'
                  e.currentTarget.style.background = 'var(--color-bg)'
                }}
              >
                <div className="flex-col gap-sm" style={{ flex: 1, minWidth: 0 }}>
                  <span className="text-sm truncate" style={{ fontWeight: 500 }}>{item.query}</span>
                  {item.battery_model && (
                    <span className="text-xs text-muted">{item.battery_model}</span>
                  )}
                </div>
                <span className="badge badge-blue text-xs flex-shrink-0">查看</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div style={{ animation: 'slideUp 0.4s ease-out 0.4s both' }}>
        <h3 className="card-title mb-lg">🚀 快速入口</h3>
        <div className="grid-4">
          {QUICK_ACTIONS.map(action => (
            <div
              key={action.path}
              onClick={() => navigate(action.path)}
              className="card"
              style={{
                cursor: 'pointer',
                textAlign: 'center',
                padding: 'var(--space-2xl)',
                borderTop: `3px solid ${action.color}`,
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.transform = 'translateY(-4px)'
                e.currentTarget.style.boxShadow = 'var(--shadow-lg)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.transform = 'translateY(0)'
                e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
              }}
            >
              <div style={{ fontSize: '32px', marginBottom: 'var(--space-md)' }}>
                {action.icon}
              </div>
              <div style={{ fontWeight: 600, fontSize: '15px', marginBottom: 'var(--space-xs)' }}>
                {action.label}
              </div>
              <div className="text-sm text-muted">{action.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="error-card mt-xl">
          <div className="error-card-title">连接异常</div>
          <div className="error-card-text">{error}</div>
        </div>
      )}
    </div>
  )
}
