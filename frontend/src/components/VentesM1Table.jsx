import { useEffect, useState } from 'react'
import { getVentesM1 } from '../services/dashboard'
import { estNeutralise, MESSAGE_NEUTRALISE } from '../utils/recommandation'

const MOIS_NOMS_FR = [
  'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
  'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre',
]

/** Nom du mois calendaire précédent (M-1), par rapport à aujourd'hui. */
function moisPrecedentFr(date = new Date()) {
  const indexPrecedent = (date.getMonth() - 1 + 12) % 12
  return MOIS_NOMS_FR[indexPrecedent]
}

function formatNb(val) {
  return new Intl.NumberFormat('fr-FR').format(Math.round(val ?? 0))
}

const STATUT_BADGE = {
  RUPTURE:   'bg-danger-light dark:bg-danger/10 text-danger',
  CRITIQUE:  'bg-orange-50 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400',
  COMMANDER: 'bg-yellow-50 dark:bg-yellow-500/10 text-yellow-700 dark:text-yellow-400',
  OK:        'bg-brand-light dark:bg-brand/10 text-brand-dark dark:text-brand',
}

/**
 * Tableau complet de tous les articles vendus le mois dernier (M-1), triés
 * du plus vendu au moins vendu — pour repérer les produits qui tournent
 * bien (best-sellers) et ceux qui restent sur l'étagère.
 */
export default function VentesM1Table() {
  const [ventes, setVentes] = useState([])
  const [chargement, setChargement] = useState(true)

  useEffect(() => {
    getVentesM1()
      .then(setVentes)
      .catch(() => setVentes([]))
      .finally(() => setChargement(false))
  }, [])

  if (chargement) {
    return <p className="text-sm text-slate-400 dark:text-slate-500">Chargement des ventes…</p>
  }
  if (ventes.length === 0) return null

  const mois = moisPrecedentFr()
  const max = ventes[0]?.vente_m1 || 1

  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200/70 dark:border-slate-700/70 overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700">
        <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
          Ventes de {mois}
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
          {ventes.length} référence{ventes.length > 1 ? 's' : ''} vendue{ventes.length > 1 ? 's' : ''}, du plus vendu au moins vendu
        </p>
      </div>

      <div className="max-h-[480px] overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-white dark:bg-slate-800">
            <tr className="text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide border-b border-slate-100 dark:border-slate-700">
              <th className="px-4 py-2.5">Désignation</th>
              <th className="px-4 py-2.5">Vendu en {mois}</th>
              <th className="px-4 py-2.5 text-right">Stock</th>
              <th className="px-4 py-2.5 text-right">Statut</th>
            </tr>
          </thead>
          <tbody>
            {ventes.map((v) => (
              <tr key={v.code} className="border-b border-slate-100 dark:border-slate-700/50 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-700/30">
                <td className="px-4 py-2.5 text-sm text-slate-800 dark:text-slate-200 max-w-xs">
                  <span className="line-clamp-1">{v.designation}</span>
                </td>
                <td className="px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    <span className="tabular-nums text-sm font-semibold text-slate-900 dark:text-slate-100 w-12 shrink-0">
                      {formatNb(v.vente_m1)}
                    </span>
                    <span className="flex-1 h-1.5 rounded-full bg-slate-100 dark:bg-slate-700 overflow-hidden max-w-[140px]">
                      <span
                        className="block h-full rounded-full bg-brand"
                        style={{ width: `${Math.max(4, (v.vente_m1 / max) * 100)}%` }}
                      />
                    </span>
                  </div>
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums text-sm text-slate-600 dark:text-slate-400">
                  {formatNb(v.stock_actuel)}
                </td>
                <td className="px-4 py-2.5 text-right">
                  <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUT_BADGE[v.statut] || STATUT_BADGE.OK}`}>
                    {v.statut}
                  </span>
                  {estNeutralise(v) && (
                    <p
                      className="mt-1 text-[11px] text-slate-400 dark:text-slate-500 italic"
                      title={MESSAGE_NEUTRALISE}
                    >
                      rotation trop rare
                    </p>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
