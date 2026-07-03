import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getUserEmail, logout } from '../services/auth'

export default function Dashboard() {
  const navigate = useNavigate()
  const [loggingOut, setLoggingOut] = useState(false)

  async function handleLogout() {
    setLoggingOut(true)
    try {
      await logout()
    } finally {
      navigate('/login', { replace: true })
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between">
        <div>
          <p className="font-semibold">SAD OFFICINE</p>
          <p className="text-sm text-slate-400">{getUserEmail()}</p>
        </div>
        <button
          onClick={handleLogout}
          disabled={loggingOut}
          className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-medium hover:bg-slate-800 disabled:opacity-60"
        >
          {loggingOut ? 'Déconnexion…' : 'Se déconnecter'}
        </button>
      </header>
      <main className="max-w-4xl mx-auto px-6 py-12 text-center">
        <h1 className="text-xl font-semibold text-slate-900">Bientôt : votre tableau de pilotage</h1>
        <p className="mt-2 text-slate-500">
          Importez votre premier fichier pour voir apparaître vos recommandations de commande.
        </p>
      </main>
    </div>
  )
}
