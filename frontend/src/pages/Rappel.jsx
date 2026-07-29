import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import { getAlertesStrategiques } from '../services/dashboard'
import { marquerDirection } from '../services/pageTransition'

function formatFCFA(val) {
  return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(val || 0) + ' FCFA'
}

function formatDateHeureFr(date) {
  const jour = new Intl.DateTimeFormat('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(date)
  const heure = new Intl.DateTimeFormat('fr-FR', { hour: '2-digit', minute: '2-digit' }).format(date)
  return `${jour} à ${heure}`
}

/**
 * Section 7.2 du cahier des charges : reprend, sous forme de page plutôt
 * que d'e-mail/WhatsApp (StockAid ne tourne pas en ligne), le message
 * quotidien exact décrit par le cahier des charges — une ou deux phrases
 * reprenant l'encart 7.0, pas un tableau détaillé (ça, c'est "Quoi
 * commander"). Ouverte en cliquant sur la cloche de la barre latérale.
 */
export default function Rappel() {
  const navigate = useNavigate()
  const [alertes, setAlertes] = useState(null)
  const [chargement, setChargement] = useState(true)

  useEffect(() => {
    getAlertesStrategiques()
      .then(setAlertes)
      .catch(() => setAlertes(null))
      .finally(() => setChargement(false))
  }, [])

  function handleVoirDetail() {
    marquerDirection('/rappel', '/quoi-commander')
    navigate('/quoi-commander', { viewTransition: true })
  }

  const nb = alertes?.nb_references || 0

  return (
    <div className="px-6 py-8 md:px-10 md:py-10 max-w-2xl mx-auto space-y-6">
      <PageHeader
        label="Rappel"
        title="Rappel quotidien"
        subtitle="Le message que StockAid vous aurait envoyé aujourd'hui."
      />

      {chargement ? (
        <p className="text-sm text-slate-400 dark:text-slate-500">Chargement…</p>
      ) : (
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
          <div className="flex items-start gap-3">
            <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${nb > 0 ? 'bg-danger-light dark:bg-danger/10 text-danger' : 'bg-brand-light dark:bg-brand/10 text-brand-dark dark:text-brand'}`}>
              <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
                <path d="M12 3.5a5.5 5.5 0 0 0-5.5 5.5v3.1c0 .5-.15.98-.44 1.39L4.6 15.4a1 1 0 0 0 .8 1.6h13.2a1 1 0 0 0 .8-1.6l-1.46-1.91a2.3 2.3 0 0 1-.44-1.39V9A5.5 5.5 0 0 0 12 3.5Z" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M9.5 19a2.5 2.5 0 0 0 5 0" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
              </svg>
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline justify-between gap-2">
                <p className="font-semibold text-slate-900 dark:text-slate-100">StockAid</p>
                <p className="text-xs text-slate-400 dark:text-slate-500 shrink-0 capitalize">{formatDateHeureFr(new Date())}</p>
              </div>

              {nb > 0 ? (
                <p className="mt-2 text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                  {nb} référence{nb > 1 ? 's' : ''} classe A/B en RUPTURE ou CRITIQUE,{' '}
                  <span className="font-semibold text-danger">{formatFCFA(alertes.ventes_perdues_totales_fcfa)}</span>{' '}
                  de ventes perdues estimées.
                </p>
              ) : (
                <p className="mt-2 text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                  Aucune référence stratégique en rupture ou critique aujourd'hui — rien à signaler.
                </p>
              )}
            </div>
          </div>

          {nb > 0 && (
            <button
              type="button"
              onClick={handleVoirDetail}
              className="tg-tap mt-5 w-full rounded-lg bg-brand-gradient px-4 py-2.5 font-semibold text-white shadow-sm transition-all hover:shadow-brand"
            >
              Voir le détail et commander
            </button>
          )}
        </div>
      )}
    </div>
  )
}
