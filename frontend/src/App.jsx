import { useState, useEffect } from 'react'
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Setup from './pages/Setup'
import Dashboard from './pages/Dashboard'
import Import from './pages/Import'
import Reglages from './pages/Reglages'
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

const router = createBrowserRouter([
  { path: '/', element: <Home /> },
  { path: '/setup', element: <Setup /> },
  { path: '/login', element: <Login /> },
  {
    path: '/dashboard',
    element: (
      <ProtectedRoute>
        <Dashboard />
      </ProtectedRoute>
    ),
  },
  {
    path: '/import',
    element: (
      <ProtectedRoute>
        <Import />
      </ProtectedRoute>
    ),
  },
  {
    path: '/reglages',
    element: (
      <ProtectedRoute>
        <Reglages />
      </ProtectedRoute>
    ),
  },
  { path: '*', element: <NotFound /> },
])

export default function App() {
  return <RouterProvider router={router} />
}
