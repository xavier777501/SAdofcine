import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getOfficineNom, logout } from '../services/auth'
import { marquerDirection } from '../services/pageTransition'
import Logo from '../components/Logo'
import ThemeToggle from '../components/ThemeToggle'

export default function Dashboard() {
  const navigate = useNavigate()
  const [loggingOut, setLoggingOut] = useState(false)

  async function handleLogout() {
    setLoggingOut(true)
    try {
      await logout()
    } finally {
      marquerDirection('/dashboard', '/login')
      navigate('/login', { replace: true, viewTransition: true })
    }
  }

  function handleImportClick() {
    marquerDirection('/dashboard', '/import')
    navigate('/import', { viewTransition: true })
  }

  return (
    <div className="min-h-screen bg-surface dark:bg-slate-900">
      <header className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Logo className="h-9 w-9 rounded-lg" />
          <div>
            <p className="brand-name text-lg leading-none text-slate-900 dark:text-slate-100">StockAid</p>
            <p className="text-sm text-slate-500 dark:text-slate-400">{getOfficineNom()}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <button
            onClick={handleLogout}
            disabled={loggingOut}
            className="tg-tap rounded-lg border border-info text-info px-4 py-2 text-sm font-medium hover:bg-info-light dark:hover:bg-info/10 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loggingOut ? 'Déconnexion…' : 'Se déconnecter'}
          </button>
        </div>
      </header>
      <main className="max-w-4xl mx-auto px-6 py-12 text-center">
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Bientôt : votre tableau de pilotage</h1>
        <p className="mt-2 text-slate-500 dark:text-slate-400">
          Importez votre premier fichier pour voir apparaître vos recommandations de commande.
        </p>
        <button
          onClick={handleImportClick}
          className="tg-tap mt-6 rounded-lg bg-brand px-5 py-2.5 font-semibold text-white transition hover:bg-brand-dark"
        >
          Importer un fichier
        </button>
      </main>
    </div>
  )
}
