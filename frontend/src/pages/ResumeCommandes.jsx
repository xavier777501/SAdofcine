import { useEffect, useMemo, useState } from 'react'
import { getVentesM1, getHistoriqueCommandes } from '../services/dashboard'
import { formatNb, texteRecommandation, estNeutralise } from '../utils/recommandation'
import PageHeader from '../components/PageHeader'

function formatDateHeureFr(iso) {
  const d = new Date(iso)
  return new Intl.DateTimeFormat('fr-FR', { dateStyle: 'medium', timeStyle: 'short' }).format(d)
}

// Section 7.3 : historique de chaque commande "validée" (export PDF/Excel) —
// qui, quand, quantité recommandée par StockAid vs quantité finalement retenue.
function HistoriqueCommandes() {
  const [commandes, setCommandes] = useState([])
  const [chargement, setChargement] = useState(true)
  const [ligneOuverte, setLigneOuverte] = useState(null)

  useEffect(() => {
    getHistoriqueCommandes()
      .then(setCommandes)
      .catch(() => setCommandes([]))
      .finally(() => setChargement(false))
  }, [])

  if (chargement) return <p className="text-sm text-slate-400 dark:text-slate-500">Chargement…</p>

  if (commandes.length === 0) {
    return (
      <p className="text-sm text-slate-400 dark:text-slate-500 py-8 text-center">
        Aucune commande exportée pour le moment — l'historique se remplit à chaque export PDF ou Excel de la liste d'action.
      </p>
    )
  }

  return (
    <div className="space-y-2">
      {commandes.map((c) => {
        const ouverte = ligneOuverte === c.id
        return (
          <div
            key={c.id}
            className="bg-white dark:bg-slate-800 rounded-xl shadow-xs border border-slate-200/70 dark:border-slate-700/70 overflow-hidden"
          >
            <button
              onClick={() => setLigneOuverte(ouverte ? null : c.id)}
              className="tg-tap w-full flex items-center gap-3 px-4 py-3 text-left"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  {formatDateHeureFr(c.date)} <span className="font-normal text-slate-400 dark:text-slate-500 text-xs uppercase">{c.format}</span>
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {c.utilisateur_email} · {c.nb_references} référence{c.nb_references > 1 ? 's' : ''}
                  {c.nb_ecarts > 0 && ` · ${c.nb_ecarts} ajustée${c.nb_ecarts > 1 ? 's' : ''} manuellement`}
                </p>
              </div>
              <svg viewBox="0 0 16 16" className={`w-4 h-4 text-slate-400 transition-transform duration-200 shrink-0 ${ouverte ? 'rotate-180' : ''}`} fill="none">
                <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
            {ouverte && (
              <div className="border-t border-slate-100 dark:border-slate-700 divide-y divide-slate-100 dark:divide-slate-700/50">
                {c.lignes.map((l, i) => (
                  <div key={i} className="flex items-center justify-between gap-3 px-4 py-2 text-sm">
                    <p className="text-slate-700 dark:text-slate-300 truncate">{l.designation}</p>
                    <p className={`shrink-0 tabular-nums ${l.qte_recommandee !== l.qte_validee ? 'text-info font-semibold' : 'text-slate-500 dark:text-slate-400'}`}>
                      {l.qte_recommandee !== l.qte_validee
                        ? `${formatNb(l.qte_recommandee)} → ${formatNb(l.qte_validee)}`
                        : formatNb(l.qte_validee)}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

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
  const [onglet, setOnglet] = useState('ventes')
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

      <div className="flex gap-2">
        {[
          { valeur: 'ventes', label: 'Résumé des ventes' },
          { valeur: 'historique', label: 'Historique des commandes' },
        ].map((o) => (
          <button
            key={o.valeur}
            onClick={() => setOnglet(o.valeur)}
            className={`tg-tap text-sm font-medium px-4 py-2 rounded-full border transition-all ${
              onglet === o.valeur
                ? 'bg-slate-800 dark:bg-slate-200 text-white dark:text-slate-900 border-transparent'
                : 'bg-transparent text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-600 hover:border-slate-300'
            }`}
          >
            {o.label}
          </button>
        ))}
      </div>

      {onglet === 'historique' && <HistoriqueCommandes />}

      {onglet === 'ventes' && chargement && <p className="text-sm text-slate-400 dark:text-slate-500">Chargement…</p>}

      {onglet === 'ventes' && !chargement && ventes.length === 0 && (
        <p className="text-sm text-slate-400 dark:text-slate-500 py-8 text-center">
          Aucune vente enregistrée pour le moment.
        </p>
      )}

      {onglet === 'ventes' && !chargement && ventes.length > 0 && (
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
