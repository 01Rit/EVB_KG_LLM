import { Link, useLocation } from 'react-router-dom'

const navItems = [
  { path: '/', label: '仪表盘' },
  { path: '/graph', label: '图谱浏览' },
  { path: '/query', label: '推理查询' },
  { path: '/sequence', label: '序列规划' },
  { path: '/import', label: '导入管理' },
  { path: '/settings', label: '参数设置' },
]

export function Sidebar() {
  const location = useLocation()

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">电池拆卸系统</div>
      <ul className="sidebar-nav">
        {navItems.map((item) => (
          <li
            key={item.path}
            className={`sidebar-nav-item ${location.pathname === item.path ? 'active' : ''}`}
          >
            <Link to={item.path} style={{ color: 'inherit', textDecoration: 'none' }}>
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </aside>
  )
}