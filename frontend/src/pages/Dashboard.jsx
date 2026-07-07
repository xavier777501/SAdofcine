import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getOfficineNom } from '../services/auth'
import { marquerDirection } from '../services/pageTransition'
import { lancerCalcul } from '../services/calcul'
import ImportHistoryTable from '../components/ImportHistoryTable'
import RepartitionStockDonut from '../components/RepartitionStockDonut'

export default function Dashboard() {
  const navigate = useNavigate()
  const [etatStock, setEtatStock] = useState(null)
  const [chargement, setChargement] = useState(true)

  useEffect(() => {
    lancerCalcul()
      .then(setEtatStock)
      .catch(() => setEtatStock(null))
      .finally(() => setChargement(false))
  }, [])

  function handleImportClick() {
    marquerDirection('/dashboard', '/import')
    navigate('/import', { viewTransition: true })
  }

  const aDesReferences = etatStock && etatStock.nb_references > 0

  return (
    <div className="px-6 py-8 md:px-10 md:py-10 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">Tableau de bord</h1>
        <p className="mt-1 text-slate-500 dark:text-slate-400 text-sm">{getOfficineNom()}</p>
      </div>

      {chargement && <p className="text-slate-400 dark:text-slate-500 text-sm">Chargement…</p>}

      {!chargement && aDesReferences && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="group bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200/70 dark:border-slate-700/70 px-6 py-5 transition-all duration-200 hover:shadow-md hover:-translate-y-1">
            <div className="flex items-center justify-between">
              <p className="text-sm text-slate-500 dark:text-slate-400">Références en rupture</p>
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-danger-light dark:bg-danger/10 transition-transform duration-200 group-hover:scale-110">
                <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4 text-danger" aria-hidden="true">
                  <path d="M12 9v4m0 4h.01M4.5 19h15a1 1 0 0 0 .87-1.5l-7.5-13a1 1 0 0 0-1.74 0l-7.5 13A1 1 0 0 0 4.5 19Z" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </span>
            </div>
            <p className="mt-3 text-3xl font-bold text-danger">{etatStock.nb_rupture}</p>
          </div>

          <div className="group bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200/70 dark:border-slate-700/70 px-6 py-5 transition-all duration-200 hover:shadow-md hover:-translate-y-1">
            <div className="flex items-center justify-between">
              <p className="text-sm text-slate-500 dark:text-slate-400">Références à commander</p>
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-orange-50 dark:bg-orange-500/10 transition-transform duration-200 group-hover:scale-110">
                <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4 text-orange-600 dark:text-orange-400" aria-hidden="true">
                  <path d="M3 3h2l.4 2M7 13h10l3-8H5.4M7 13 5.4 5M7 13l-1.7 3.4A1 1 0 0 0 6.2 18H17M9 21a1 1 0 1 0 0-2 1 1 0 0 0 0 2Zm8 0a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </span>
            </div>
            <p className="mt-3 text-3xl font-bold text-orange-600 dark:text-orange-400">{etatStock.nb_a_commander}</p>
          </div>

          <div className="group bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200/70 dark:border-slate-700/70 px-6 py-5 transition-all duration-200 hover:shadow-md hover:-translate-y-1">
            <div className="flex items-center justify-between">
              <p className="text-sm text-slate-500 dark:text-slate-400">Total références calculées</p>
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 dark:bg-slate-700 transition-transform duration-200 group-hover:scale-110">
                <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4 text-slate-500 dark:text-slate-400" aria-hidden="true">
                  <path d="M4 13h6V4H4v9Zm0 7h6v-5H4v5Zm10 0h6V11h-6v9Zm0-16v5h6V4h-6Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
                </svg>
              </span>
            </div>
            <p className="mt-3 text-3xl font-bold text-slate-700 dark:text-slate-300">{etatStock.nb_references}</p>
          </div>
        </div>
      )}

      {!chargement && aDesReferences && (
        <RepartitionStockDonut
          nbRupture={etatStock.nb_rupture}
          nbACommander={etatStock.nb_a_commander}
          nbReferences={etatStock.nb_references}
        />
      )}

      {!chargement && (
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200/70 dark:border-slate-700/70 px-8 py-8 flex flex-col md:flex-row items-center gap-6 transition-all duration-200 hover:shadow-md hover:-translate-y-1">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-brand-light dark:bg-brand/10">
            <svg viewBox="0 0 24 24" fill="none" className="h-8 w-8 text-brand" aria-hidden="true">
              <path
                d="M12 4v10m0 0-3.5-3.5M12 14l3.5-3.5M5 17v1.5A1.5 1.5 0 0 0 6.5 20h11a1.5 1.5 0 0 0 1.5-1.5V17"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <div className="flex-1 text-center md:text-left">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {aDesReferences ? `Bonjour, ${getOfficineNom()} !` : 'Bienvenue sur StockAid'}
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {aDesReferences
                ? "La liste détaillée de vos recommandations arrivera avec le tableau de pilotage complet. En attendant, réimportez régulièrement pour garder vos chiffres à jour."
                : 'Importez votre premier fichier pour voir apparaître vos recommandations de commande.'}
            </p>
          </div>
          <button
            onClick={handleImportClick}
            className="tg-tap shrink-0 rounded-lg bg-brand-gradient px-5 py-2.5 font-semibold text-white shadow-sm transition-all hover:shadow-brand hover:-translate-y-0.5"
          >
            {aDesReferences ? 'Importer un nouveau fichier' : 'Importer un fichier'}
          </button>
        </div>
      )}

      <ImportHistoryTable />
    </div>
  )
}
