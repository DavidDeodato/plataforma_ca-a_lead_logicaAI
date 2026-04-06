import { Activity, LayoutDashboard, Menu, MessageSquare, Search, Settings2, Star, Users } from 'lucide-react'
import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/leads', label: 'Leads', icon: Users },
  { to: '/qualified', label: 'Qualificados', icon: Star },
  { to: '/conversations', label: 'Conversas', icon: MessageSquare },
  { to: '/automation', label: 'Automação', icon: Activity },
  { to: '/settings', label: 'Configuração', icon: Settings2 },
  { to: '/prospecting', label: 'Pesquisa de clientes', icon: Search },
]

export function AppShell() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  return (
    <div className={`app-shell ${sidebarCollapsed ? 'app-shell--collapsed' : ''}`}>
      <aside id="app-sidebar" className={`sidebar ${sidebarCollapsed ? 'sidebar--collapsed' : ''}`}>
        <div className="sidebar__brand">
          <img className="sidebar__brand-full" src="/nexlead-logo-full.png" alt="NexLead" />
          <span className="sidebar__brand-tag">Cockpit comercial</span>
        </div>
        <nav className="sidebar__nav">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) => `sidebar__link ${isActive ? 'sidebar__link--active' : ''}`}
            >
              <Icon size={18} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="content">
        <button
          className="content__sidebar-toggle"
          type="button"
          onClick={() => setSidebarCollapsed((current) => !current)}
          aria-label={sidebarCollapsed ? 'Abrir menu lateral' : 'Fechar menu lateral'}
          aria-expanded={!sidebarCollapsed}
          aria-controls="app-sidebar"
        >
          <Menu size={18} />
        </button>
        <Outlet />
      </main>
    </div>
  )
}
