import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getOfficineNom, logout } from '../services/auth'
import { marquerDirection } from '../services/pageTransition'
import { lancerCalcul } from '../services/calcul'
import Logo from '../components/Logo'
import ThemeToggle from '../components/ThemeToggle'

export default function Dashboard() {
  const navigate = useNavigate()
  const [loggingOut, setLoggingOut] = useState(false)
  const [etatStock, setEtatStock] = useState(null)
  const [chargement, setChargement] = useState(true)

  useEffect(() => {
    lancerCalcul()
      .then(setEtatStock)
      .catch(() => setEtatStock(null))
      .finally(() => setChargement(false))
  }, [])

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

  function handleReglagesClick() {
    marquerDirection('/dashboard', '/reglages')
    navigate('/reglages', { viewTransition: true })
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
            onClick={handleReglagesClick}
            className="tg-tap rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 px-4 py-2 text-sm font-medium shadow-xs transition-all hover:shadow-sm hover:-translate-y-0.5 hover:bg-slate-50 dark:hover:bg-slate-700"
          >
            Réglages
          </button>
          <button
            onClick={handleLogout}
            disabled={loggingOut}
            className="tg-tap rounded-lg border border-info text-info px-4 py-2 text-sm font-medium transition-all hover:shadow-info hover:-translate-y-0.5 hover:bg-info-light dark:hover:bg-info/10 disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0 disabled:hover:shadow-none"
          >
            {loggingOut ? 'Déconnexion…' : 'Se déconnecter'}
          </button>
        </div>
      </header>
      <main className="max-w-4xl mx-auto px-6 py-12">
        {chargement && <p className="text-center text-slate-400 dark:text-slate-500 text-sm">Chargement…</p>}

        {!chargement && (!etatStock || etatStock.nb_references === 0) && (
          <div className="max-w-lg mx-auto text-center bg-white dark:bg-slate-800 rounded-2xl shadow-md border border-slate-200/70 dark:border-slate-700/70 px-8 py-12">
            <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-light dark:bg-brand/10">
              <svg viewBox="0 0 24 24" fill="none" className="h-7 w-7 text-brand" aria-hidden="true">
                <path
                  d="M12 4v10m0 0-3.5-3.5M12 14l3.5-3.5M5 17v1.5A1.5 1.5 0 0 0 6.5 20h11a1.5 1.5 0 0 0 1.5-1.5V17"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Bientôt : votre tableau de pilotage</h1>
            <p className="mt-2 text-slate-500 dark:text-slate-400">
              Importez votre premier fichier pour voir apparaître vos recommandations de commande.
            </p>
            <button
              onClick={handleImportClick}
              className="tg-tap mt-6 rounded-lg bg-brand-gradient px-5 py-2.5 font-semibold text-white shadow-sm transition-all hover:shadow-brand hover:-translate-y-0.5"
            >
              Importer un fichier
            </button>
          </div>
        )}

        {!chargement && etatStock && etatStock.nb_references > 0 && (
          <div className="space-y-6">
            <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">État du stock</h1>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200/70 dark:border-slate-700/70 px-6 py-5">
                <p className="text-3xl font-bold text-danger">{etatStock.nb_rupture}</p>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Références en rupture</p>
              </div>
              <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200/70 dark:border-slate-700/70 px-6 py-5">
                <p className="text-3xl font-bold text-orange-600 dark:text-orange-400">{etatStock.nb_a_commander}</p>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Références à commander</p>
              </div>
              <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200/70 dark:border-slate-700/70 px-6 py-5">
                <p className="text-3xl font-bold text-slate-500 dark:text-slate-400">{etatStock.nb_references}</p>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Total références calculées</p>
              </div>
            </div>
            <p className="text-sm text-slate-400 dark:text-slate-500">
              La liste détaillée avec le détail de chaque référence arrivera avec le tableau de pilotage complet.
            </p>
            <button
              onClick={handleImportClick}
              className="tg-tap rounded-lg border border-brand px-4 py-2.5 font-semibold text-brand transition hover:bg-brand-light dark:hover:bg-brand/10"
            >
              Importer un nouveau fichier
            </button>
          </div>
        )}
      </main>
    </div>
  )
}
