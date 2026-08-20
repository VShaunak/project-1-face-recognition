import { LogOut, Menu, Moon, Sun, Home, UserPlus, Video, Clock, Users, BarChart3, Settings } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { useState } from 'react'

interface SidebarProps { systemStatus: any; darkMode: boolean; onToggleDarkMode: () => void; onLogout: () => void }

export default function Sidebar({ systemStatus, darkMode, onToggleDarkMode, onLogout }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false); const location = useLocation()
  const items = [{ icon: Home, label: 'Dashboard', path: '/dashboard' },{ icon: UserPlus, label: 'Register Person', path: '/register' },{ icon: Video, label: 'Live Recognition', path: '/recognition' },{ icon: Clock, label: 'Attendance', path: '/attendance' },{ icon: Users, label: 'Users', path: '/users' },{ icon: BarChart3, label: 'Analytics', path: '/analytics' },{ icon: Settings, label: 'Settings', path: '/settings' }]
  return <aside className={`face-sidebar${collapsed ? ' collapsed' : ''}`}><div className="brand-row"><span className="brand-name">{collapsed ? 'FA' : 'FaceAttend'}</span><button className="icon-button" onClick={() => setCollapsed(!collapsed)} aria-label="Toggle navigation"><Menu size={20}/></button></div>{!collapsed && <div className="status-box"><span>REGISTERED PEOPLE</span><strong>{systemStatus?.registered_users ?? 0}</strong><span>TODAY&apos;S ATTENDANCE</span><strong>{systemStatus?.todays_attendance ?? 0}</strong></div>}<nav className="side-nav">{items.map((item) => <Link key={item.path} to={item.path} className={`side-link${location.pathname === item.path ? ' active' : ''}`} title={item.label}><item.icon size={19}/>{!collapsed && item.label}</Link>)}</nav><div className="side-actions"><button className="side-action" onClick={onToggleDarkMode}>{darkMode ? <Sun size={19}/> : <Moon size={19}/>}{!collapsed && (darkMode ? 'Light mode' : 'Dark mode')}</button><button className="side-action danger" onClick={onLogout}><LogOut size={19}/>{!collapsed && 'Log out'}</button></div></aside>
}
