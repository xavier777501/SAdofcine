import { useEffect, useMemo, useState } from 'react'
import { getVentesM1 } from '../services/dashboard'
import { formatNb, texteRecommandation, estNeutralise } from '../utils/recommandation'
import PageHeader from '../components/PageHeader'

const MOIS_NOMS_FR = [
  'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
  'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre',
]

function moisPrecedentFr(date = new Date()) {
  return MOIS_NOMS_FR[(date.getMonth() - 1 + 12) % 12]
}

const STATUT_STYLE = {
  RUPTURE:   { barre: 'bg-danger',  texte: 'text-danger',                    label: 'Rupture' },
  CRITIQUE:  { barre: 'bg-orange-500', texte: 'text-orange-600 dark:text-orange-400', label: 'Critique' },
  COMMANDER: { barre: 'bg-yellow-400', texte: 'text-yellow-700 dark:text-yellow-400', label: 'À commander' },
  OK:        { barre: 'bg-brand',   texte: 'text-brand-dark dark:text-brand', label: 'OK' },
}

const FILTRES = ['TOUS', 'RUPTURE', 'CRITIQUE', 'COMMANDER', 'OK']

export default function ResumeCommandes() {
  const [ventes, setVentes] = useState([])
  const [chargement, setChargement] = useState(true)
  const [recherche, setRecherche] = useState('')
  const [filtreStatut, setFiltreStatut] = useState('TOUS')

  useEffect(() => {
    getVentesM1()
      .then(setVentes)
      .catch(() => setVentes([]))
      .finally(() => setChargement(false))
  }, [])

  const mois = moisPrecedentFr()

  const listeFiltree = useMemo(() => {
    const rechercheNorm = recherche.trim().toLowerCase()
    return ventes.filter((v) => {
      if (filtreStatut !== 'TOUS' && v.statut !== filtreStatut) return false
      if (rechercheNorm && !v.designation.toLowerCase().includes(rechercheNorm) && !v.code.toLowerCase().includes(rechercheNorm)) {
        return false
      }
      return true
    })
  }, [ventes, recherche, filtreStatut])

  return (
    <div className="px-6 py-8 md:px-10 md:py-10 max-w-4xl mx-auto space-y-6">
      <PageHeader
        label="Résumé des commandes"
        title="Résumé des commandes"
        subtitle={`Basé sur vos ventes de ${mois} — un rappel produit par produit de ce que vous pouvez commander`}
      />

      {chargement && <p className="text-sm text-slate-400 dark:text-slate-500">Chargement…</p>}

      {!chargement && ventes.length === 0 && (
        <p className="text-sm text-slate-400 dark:text-slate-500 py-8 text-center">
          Aucune vente enregistrée pour le moment.
        </p>
      )}

      {!chargement && ventes.length > 0 && (
        <>
          <div className="flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
            <input
              type="text"
              value={recherche}
              onChange={(e) => setRecherche(e.target.value)}
              placeholder="Rechercher un produit ou un code…"
              className="w-full sm:max-w-xs rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 shadow-xs focus:outline-none focus:border-brand focus:shadow-[0_0_0_4px_var(--color-brand-light)]"
            />
            <div className="flex items-center gap-2 flex-wrap">
              {FILTRES.map((s) => {
                const actif = filtreStatut === s
                const cfg = STATUT_STYLE[s]
                return (
                  <button
                    key={s}
                    onClick={() => setFiltreStatut(s)}
                    className={`tg-tap text-xs font-medium px-3 py-1.5 rounded-full border transition-all ${
                      actif
                        ? s === 'TOUS'
                          ? 'bg-slate-800 dark:bg-slate-200 text-white dark:text-slate-900 border-transparent'
                          : `${cfg.barre} text-white border-transparent`
                        : 'bg-transparent text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-600 hover:border-slate-300'
                    }`}
                  >
                    {s === 'TOUS' ? 'Tous' : cfg.label}
                  </button>
                )
              })}
            </div>
          </div>

          <p className="text-xs text-slate-400 dark:text-slate-500">
            {listeFiltree.length} référence{listeFiltree.length > 1 ? 's' : ''}
          </p>

          <div className="space-y-3">
            {listeFiltree.length === 0 ? (
              <p className="text-sm text-slate-400 dark:text-slate-500 py-8 text-center">
                Aucun résultat pour cette recherche.
              </p>
            ) : (
              listeFiltree.map((v) => {
                const style = STATUT_STYLE[v.statut] || STATUT_STYLE.OK
                const neutralise = estNeutralise(v)
                return (
                  <div
                    key={v.code}
                    className="flex gap-3 bg-white dark:bg-slate-800 rounded-xl shadow-xs border border-slate-200/70 dark:border-slate-700/70 px-4 py-3 transition-all duration-200 hover:shadow-sm"
                  >
                    <span className={`w-1 shrink-0 rounded-full ${neutralise ? 'bg-slate-300 dark:bg-slate-600' : style.barre}`} />
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                        {v.designation} <span className="font-normal text-slate-400 dark:text-slate-500 text-xs">({v.code})</span>
                      </p>
                      <p className="mt-0.5 text-sm text-slate-600 dark:text-slate-300">
                        Vous avez vendu {formatNb(v.vente_m1)} unités en {mois}.
                      </p>
                      <p className={`mt-0.5 text-sm font-medium ${neutralise ? 'text-slate-500 dark:text-slate-400 italic' : style.texte}`}>
                        {texteRecommandation(v)}
                      </p>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </>
      )}
    </div>
  )
}
