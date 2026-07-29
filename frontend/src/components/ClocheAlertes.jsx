import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getAlertesStrategiques } from '../services/dashboard'
import { marquerDirection } from '../services/pageTransition'

function formatFCFA(val) {
  return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(val || 0) + ' FCFA'
}

/**
 * Section 7.2 du cahier des charges : décision délibérée de remplacer la
 * notification active (e-mail/WhatsApp) par cette cloche — StockAid ne
 * tourne pas en ligne, pas de serveur permanent pour un envoi à heure fixe
 * ni pour joindre le pharmacien hors de l'application. Reprend le même
 * contenu que le message aurait dû avoir (nombre de références classe A/B
 * en RUPTURE/CRITIQUE + ventes perdues estimées en FCFA), affiché en
 * permanence dans la barre latérale plutôt qu'envoyé une fois par jour.
 * N'affiche un badge que si nb_references > 0 (le cahier des charges
 * prévoit d'omettre le message si X = 0 — ici, pas de badge du tout).
 * Ouvre "/rappel", une page qui reprend le message tel qu'il aurait dû
 * être envoyé (une ou deux phrases), pas le détail complet de la liste.
 */
export default function ClocheAlertes({ currentPath }) {
  const navigate = useNavigate()
  const [alertes, setAlertes] = useState(null)

  useEffect(() => {
    getAlertesStrategiques()
      .then(setAlertes)
      .catch(() => setAlertes(null))
  }, [currentPath])

  const nb = alertes?.nb_references || 0

  function handleClick() {
    marquerDirection(currentPath, '/rappel')
    navigate('/rappel', { viewTransition: true })
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      title={
        nb > 0
          ? `${nb} référence(s) classe A/B en RUPTURE ou CRITIQUE, ${formatFCFA(alertes.ventes_perdues_totales_fcfa)} de ventes perdues estimées`
          : 'Aucune alerte stratégique'
      }
      className="tg-tap fixed bottom-4 right-4 z-50 flex h-11 w-11 items-center justify-center rounded-full bg-white dark:bg-slate-800 text-slate-500 dark:text-slate-300 shadow-lg border border-slate-200 dark:border-slate-700 transition-colors hover:text-danger"
    >
      <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
        <path d="M12 3.5a5.5 5.5 0 0 0-5.5 5.5v3.1c0 .5-.15.98-.44 1.39L4.6 15.4a1 1 0 0 0 .8 1.6h13.2a1 1 0 0 0 .8-1.6l-1.46-1.91a2.3 2.3 0 0 1-.44-1.39V9A5.5 5.5 0 0 0 12 3.5Z" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M9.5 19a2.5 2.5 0 0 0 5 0" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
      {nb > 0 && (
        <span className="absolute -top-1 -right-1 flex h-4.5 min-w-[18px] items-center justify-center rounded-full bg-danger px-1 text-[10px] font-bold text-white">
          {nb > 99 ? '99+' : nb}
        </span>
      )}
    </button>
  )
}
