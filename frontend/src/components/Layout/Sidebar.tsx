import { Link, useLocation } from 'react-router-dom'

const navItems = [
  { path: '/', label: '仪表盘', icon: '📊' },
  { path: '/graph', label: '图谱浏览', icon: '🕸️' },
  { path: '/query', label: '推理查询', icon: '🔍' },
  { path: '/sequence', label: '序列规划', icon: '⚡' },
  { path: '/import', label: '导入管理', icon: '📥' },
  { path: '/evaluation', label: '可拆卸性评价', icon: '📋' },
  { path: '/settings', label: '参数设置', icon: '⚙️' },
]

export function Sidebar() {
  const location = useLocation()

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">⚡</div>
        <span className="sidebar-logo-text">电池拆卸系统</span>
      </div>
      <ul className="sidebar-nav">
        {navItems.map((item) => (
          <li
            key={item.path}
            className={`sidebar-nav-item ${location.pathname === item.path ? 'active' : ''}`}
          >
            <Link to={item.path} style={{ color: 'inherit', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '12px', width: '100%' }}>
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </aside>
  )
}
