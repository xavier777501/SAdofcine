import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getAlertesStrategiques, inclureToutAlertesStrategiques } from '../services/dashboard'
import { marquerDirection } from '../services/pageTransition'

function formatFCFA(val) {
  if (!val && val !== 0) return '—'
  return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(val) + ' FCFA'
}

/**
 * Section 7.0 du cahier des charges — révèle les références classe A/B en
 * RUPTURE/CRITIQUE et estime la vente perdue en FCFA. Affiché en haut de la
 * page "Quoi commander", pour rester bien visible sans se mêler aux tuiles
 * KPI du tableau de bord.
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
      // Navigation vers "Liste d'action" plutôt qu'un simple rechargement sur
      // place : c'est là que l'effet du bouton se voit vraiment (badge "hors
      // plafond", inclusion forcée malgré le plafond budgétaire ou le mode
      // commande ciblée) — rester sur "Quoi commander" ne montrait rien de
      // nouveau puisque ces références y étaient déjà visibles.
      marquerDirection('/quoi-commander', '/liste-action')
      navigate('/liste-action', { viewTransition: true })
    } finally {
      setCommandeEnCours(false)
    }
  }

  if (chargement || !alertes) return null

  if (alertes.nb_references === 0) {
    return (
      <div className="rounded-2xl bg-brand-light dark:bg-brand/10 border border-brand/20 px-5 py-3.5 flex items-center gap-3">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-white dark:bg-slate-800 text-brand-dark dark:text-brand">
          <svg viewBox="0 0 24 24" fill="none" className="h-3.5 w-3.5" aria-hidden="true">
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
    <div className="rounded-2xl bg-danger-light dark:bg-danger/10 border-2 border-danger/30 px-5 py-4 space-y-3.5">
      <div className="flex items-start gap-3">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white dark:bg-slate-800 text-danger">
          <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true">
            <path d="M12 9v4m0 4h.01M4.5 19h15a1 1 0 0 0 .87-1.5l-7.5-13a1 1 0 0 0-1.74 0l-7.5 13A1 1 0 0 0 4.5 19Z" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
        <p className="text-sm font-semibold text-danger">
          {alertes.nb_references} référence{alertes.nb_references > 1 ? 's' : ''} classe A ou B en RUPTURE ou CRITIQUE — à commander en urgence
        </p>
      </div>

      <div className="rounded-lg bg-white/70 dark:bg-slate-900/40 divide-y divide-danger/10 max-h-56 overflow-y-auto">
        {alertes.references.map((ref) => (
          <div key={ref.id} className="flex items-center justify-between gap-3 px-3.5 py-2 text-sm">
            <div className="min-w-0">
              <p className="font-medium text-slate-800 dark:text-slate-200 truncate">{ref.designation}</p>
              <p className="text-xs text-slate-400 dark:text-slate-500">
                Classe {ref.classe} · {ref.statut === 'RUPTURE' ? 'Rupture' : 'Critique'} depuis ~{ref.jours_rupture} j
              </p>
            </div>
            <p className="shrink-0 text-sm font-semibold text-danger tabular-nums">{formatFCFA(ref.ventes_perdues_fcfa)}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="group relative inline-flex items-center gap-1.5">
          <p className="text-sm text-danger">
            Ventes perdues estimées sur cette période :{' '}
            <span className="font-bold tabular-nums">{formatFCFA(alertes.ventes_perdues_totales_fcfa)}</span>{' '}
            <span className="text-xs text-danger/70">(estimé)</span>
          </p>
          <span
            tabIndex={0}
            className="flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full border border-danger/40 text-[9px] font-semibold text-danger/70 cursor-help"
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
          className="tg-tap rounded-lg bg-danger px-3.5 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:shadow-md hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {commandeEnCours ? 'Ajout en cours…' : 'Commander ces références'}
        </button>
      </div>
    </div>
  )
}
