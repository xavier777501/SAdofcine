import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getOfficineNom, logout } from '../services/auth'
import Logo from '../components/Logo'

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
    <div className="min-h-screen bg-surface">
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Logo className="h-9 w-9 rounded-lg" />
          <div>
            <p className="brand-name text-lg leading-none text-slate-900">StockAid</p>
            <p className="text-sm text-slate-500">{getOfficineNom()}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          disabled={loggingOut}
          className="rounded-lg border border-info text-info px-4 py-2 text-sm font-medium hover:bg-info-light disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loggingOut ? 'Déconnexion…' : 'Se déconnecter'}
        </button>
      </header>
      <main className="max-w-4xl mx-auto px-6 py-12 text-center">
        <h1 className="text-xl font-semibold text-slate-900">Bientôt : votre tableau de pilotage</h1>
        <p className="mt-2 text-slate-500">
          Importez votre premier fichier pour voir apparaître vos recommandations de commande.
        </p>
        <button
          onClick={() => navigate('/import')}
          className="mt-6 rounded-lg bg-brand px-5 py-2.5 font-semibold text-white transition hover:bg-brand-dark"
        >
          Importer un fichier
        </button>
      </main>
    </div>
  )
}
