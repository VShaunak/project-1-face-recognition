import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import axios from 'axios'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import RegisterPerson from './pages/RegisterPerson'
import LiveRecognition from './pages/LiveRecognition'
import AttendanceHistory from './pages/AttendanceHistory'
import Users from './pages/Users'
import Analytics from './pages/Analytics'
import Settings from './pages/Settings'
import Login from './pages/Login'

const API_BASE_URL = 'http://localhost:8000'

interface AuthContextType {
  token: string | null
  isAuthenticated: boolean
  login: (token: string) => void
  logout: () => void
}

export const AuthContext = React.createContext<AuthContextType | undefined>(undefined)

function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'))
  const [systemStatus, setSystemStatus] = useState<any>(null)
  const [darkMode, setDarkMode] = useState(localStorage.getItem('darkMode') === 'true')

  useEffect(() => {
    if (token) {
      fetchSystemStatus()
      const interval = setInterval(fetchSystemStatus, 30000) // Refresh every 30s
      return () => clearInterval(interval)
    }
  }, [token])

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    localStorage.setItem('darkMode', String(darkMode))
  }, [darkMode])

  const fetchSystemStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/system/status`)
      setSystemStatus(response.data)
    } catch (error) {
      console.error('Failed to fetch system status:', error)
    }
  }

  const handleLogin = (token: string) => {
    setToken(token)
    localStorage.setItem('token', token)
  }

  const handleLogout = () => {
    setToken(null)
    localStorage.removeItem('token')
  }

  const authValue: AuthContextType = {
    token,
    isAuthenticated: !!token,
    login: handleLogin,
    logout: handleLogout
  }

  if (!token) {
    return (
      <Router>
        <Routes>
          <Route path="/login" element={<Login onLogin={handleLogin} />} />
          <Route path="*" element={<Navigate to="/login" />} />
        </Routes>
      </Router>
    )
  }

  return (
    <AuthContext.Provider value={authValue}>
      <Router>
        <div className={`face-app ${darkMode ? 'dark' : ''}`}>
          <Sidebar 
            systemStatus={systemStatus} 
            darkMode={darkMode}
            onToggleDarkMode={() => setDarkMode(!darkMode)}
            onLogout={handleLogout}
          />
          <main className="face-main">
            <Routes>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/register" element={<RegisterPerson />} />
              <Route path="/recognition" element={<LiveRecognition />} />
              <Route path="/attendance" element={<AttendanceHistory />} />
              <Route path="/users" element={<Users />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/login" element={<Navigate to="/dashboard" replace />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </main>
        </div>
      </Router>
    </AuthContext.Provider>
  )
}

export default App
