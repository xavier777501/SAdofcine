import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getAlertesStrategiques, inclureToutAlertesStrategiques } from '../services/dashboard'
import { marquerDirection } from '../services/pageTransition'

function formatFCFA(val) {
  if (!val && val !== 0) return '—'
  return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(val) + ' FCFA'
}

/**
 * Section 7.0 du cahier des charges — priorité absolue d'affichage : révèle
 * les références classe A/B en RUPTURE/CRITIQUE et estime la vente perdue en
 * FCFA. C'est l'argument de valeur central de StockAid, donc affiché avant
 * même les tuiles KPI sur le tableau de bord.
 */
export default function AlerteStrategique() {
  const navigate = useNavigate()
  const [alertes, setAlertes] = useState(null)
  const [chargement, setChargement] = useState(true)
  const [commandeEnCours, setCommandeEnCours] = useState(false)

  useEffect(() => {
    getAlertesStrategiques()
      .then(setAlertes)
      .catch(() => setAlertes(null))
      .finally(() => setChargement(false))
  }, [])

  async function handleCommanderCesReferences() {
    setCommandeEnCours(true)
    try {
      await inclureToutAlertesStrategiques()
      marquerDirection('/dashboard', '/quoi-commander')
      navigate('/quoi-commander', { viewTransition: true })
    } finally {
      setCommandeEnCours(false)
    }
  }

  if (chargement || !alertes) return null

  if (alertes.nb_references === 0) {
    return (
      <div className="rounded-2xl border border-brand/30 bg-brand-light dark:bg-brand/10 px-6 py-4 flex items-center gap-3">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white dark:bg-slate-800 text-brand-dark dark:text-brand">
          <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true">
            <path d="M5 13l4 4L19 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
        <p className="text-sm font-semibold text-brand-dark dark:text-brand">
          Aucune rupture critique détectée — votre stock stratégique est sous contrôle.
        </p>
      </div>
    )
  }

  return (
    <div className="rounded-2xl border-2 border-danger/40 bg-danger-light dark:bg-danger/10 px-6 py-5 space-y-4">
      <div className="flex items-start gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white dark:bg-slate-800 text-danger">
          <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
            <path d="M12 9v4m0 4h.01M4.5 19h15a1 1 0 0 0 .87-1.5l-7.5-13a1 1 0 0 0-1.74 0l-7.5 13A1 1 0 0 0 4.5 19Z" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
        <div>
          <p className="text-base font-bold text-danger">
            {alertes.nb_references} référence{alertes.nb_references > 1 ? 's' : ''} classe A ou B en RUPTURE ou CRITIQUE — à commander en urgence
          </p>
          <p className="mt-1 text-xs text-danger/80">
            Ce sont des produits importants que vous êtes en train de rater.
          </p>
        </div>
      </div>

      <div className="rounded-xl bg-white/70 dark:bg-slate-900/40 divide-y divide-danger/10 max-h-64 overflow-y-auto">
        {alertes.references.map((ref) => (
          <div key={ref.id} className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm">
            <div className="min-w-0">
              <p className="font-medium text-slate-800 dark:text-slate-200 truncate">{ref.designation}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Classe {ref.classe} · {ref.statut === 'RUPTURE' ? 'Rupture' : 'Critique'} depuis ~{ref.jours_rupture} j
              </p>
            </div>
            <p className="shrink-0 font-semibold text-danger tabular-nums">{formatFCFA(ref.ventes_perdues_fcfa)}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
        <div className="group relative inline-flex items-center gap-1.5">
          <p className="text-sm">
            <span className="text-slate-600 dark:text-slate-300">Ventes perdues estimées sur cette période : </span>
            <span className="text-lg font-extrabold text-danger tabular-nums">
              {formatFCFA(alertes.ventes_perdues_totales_fcfa)}
            </span>
            <span className="ml-1 text-xs text-slate-400 dark:text-slate-500">(estimé)</span>
          </p>
          <span
            tabIndex={0}
            className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-slate-300 dark:border-slate-600 text-[10px] font-semibold text-slate-400 dark:text-slate-500 cursor-help"
          >
            i
            <span className="pointer-events-none absolute bottom-full left-0 mb-2 w-64 rounded-lg bg-slate-800 dark:bg-slate-700 px-3 py-2 text-xs text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
              Estimation basée sur votre consommation moyenne des 12 derniers mois — pas une valeur comptable.
            </span>
          </span>
        </div>

        <button
          onClick={handleCommanderCesReferences}
          disabled={commandeEnCours}
          className="tg-tap rounded-lg bg-danger px-4 py-2.5 font-semibold text-white shadow-sm transition-all hover:shadow-md hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {commandeEnCours ? 'Ajout en cours…' : 'Commander ces références'}
        </button>
      </div>
    </div>
  )
}
