import { useState, useEffect } from 'react'
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Setup from './pages/Setup'
import ForgotPassword from './pages/ForgotPassword'
import Bienvenue from './pages/Bienvenue'
import Dashboard from './pages/Dashboard'
import ListeAction from './pages/ListeAction'
import DecisionsCommande from './pages/DecisionsCommande'
import ResumeCommandes from './pages/ResumeCommandes'
import Stock from './pages/Stock'
import Import from './pages/Import'
import Reglages from './pages/Reglages'
import Aide from './pages/Aide'
import NotFound from './pages/NotFound'
import ProtectedRoute from './components/ProtectedRoute'
import AppShell from './components/AppShell'
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
  { path: '/mot-de-passe-oublie', element: <ForgotPassword /> },
  {
    path: '/bienvenue',
    element: (
      <ProtectedRoute>
        <Bienvenue />
      </ProtectedRoute>
    ),
  },
  {
    path: '/dashboard',
    element: (
      <ProtectedRoute>
        <AppShell>
          <Dashboard />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/liste-action',
    element: (
      <ProtectedRoute>
        <AppShell>
          <ListeAction />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/quoi-commander',
    element: (
      <ProtectedRoute>
        <AppShell>
          <DecisionsCommande />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/resume-commandes',
    element: (
      <ProtectedRoute>
        <AppShell>
          <ResumeCommandes />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/stock',
    element: (
      <ProtectedRoute>
        <AppShell>
          <Stock />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/import',
    element: (
      <ProtectedRoute>
        <AppShell>
          <Import />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/reglages',
    element: (
      <ProtectedRoute>
        <AppShell>
          <Reglages />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/aide',
    element: (
      <ProtectedRoute>
        <AppShell>
          <Aide />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  { path: '*', element: <NotFound /> },
])

export default function App() {
  return <RouterProvider router={router} />
}
