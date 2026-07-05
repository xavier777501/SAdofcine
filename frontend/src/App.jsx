import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Setup from './pages/Setup'
import Dashboard from './pages/Dashboard'
import NotFound from './pages/NotFound'
import ProtectedRoute from './components/ProtectedRoute'
import { isAuthenticated, checkIsSetup } from './services/auth'

function Home() {
  const [target, setTarget] = useState(null)

  useEffect(() => {
    if (isAuthenticated()) {
      setTarget('/dashboard')
      return
    }
    checkIsSetup()
      .then(({ configured }) => setTarget(configured ? '/login' : '/setup'))
      .catch(() => setTarget('/login'))
  }, [])

  if (!target) return null
  return <Navigate to={target} replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/setup" element={<Setup />} />
        <Route path="/login" element={<Login />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  )
}
