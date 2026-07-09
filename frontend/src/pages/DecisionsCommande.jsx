import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import { getListeAction, getANePasCommander } from '../services/dashboard'
import { marquerDirection } from '../services/pageTransition'

function formatFCFA(val) {
  if (!val && val !== 0) return '—'
  return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(val) + ' FCFA'
}

const STATUT_CFG = {
  RUPTURE:   { badge: 'bg-danger text-white',    label: 'Rupture' },
  CRITIQUE:  { badge: 'bg-orange-500 text-white', label: 'Critique' },
  COMMANDER: { badge: 'bg-yellow-400 dark:bg-yellow-500 text-slate-900', label: 'Commander' },
}

export default function DecisionsCommande() {
  const [aCommander, setACommander] = useState([])
  const [neSourcePasCommander, setNePasCommander] = useState([])
  const [chargement, setChargement] = useState(true)

  useEffect(() => {
    Promise.all([getListeAction(), getANePasCommander()])
      .then(([liste, nePasCommander]) => {
        setACommander(liste)
        setNePasCommander(nePasCommander)
      })
      .catch(() => {
        setACommander([])
        setNePasCommander([])
      })
      .finally(() => setChargement(false))
  }, [])

  const urgents = aCommander.filter((l) => l.statut === 'RUPTURE' || l.statut === 'CRITIQUE').slice(0, 8)
  const totalImmobilise = neSourcePasCommander.reduce((s, l) => s + (l.tresorerie_immobilisee || 0), 0)

  return (
    <div className="px-6 py-8 md:px-10 md:py-10 max-w-4xl mx-auto space-y-6">
      <PageHeader
        label="Quoi commander"
        title="Quoi commander ?"
        subtitle="Ce qu'il faut commander en priorité, et ce qu'il ne faut surtout pas recommander."
      />

      {chargement && <p className="text-sm text-slate-400 dark:text-slate-500">Chargement…</p>}

      {!chargement && (
        <>
          {/* ── À commander en priorité ─────────────────────────────────── */}
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200/70 dark:border-slate-700/70 p-6">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">À commander en priorité</h2>
              <Link
                to="/liste-action"
                viewTransition
                onClick={() => marquerDirection('/quoi-commander', '/liste-action')}
                className="tg-tap text-sm font-medium text-brand hover:underline"
              >
                Voir la liste complète →
              </Link>
            </div>

            {aCommander.length === 0 ? (
              <p className="mt-3 text-sm text-slate-400 dark:text-slate-500">Rien à commander pour l'instant.</p>
            ) : (
              <div className="mt-4 space-y-2.5">
                {urgents.map((l) => {
                  const cfg = STATUT_CFG[l.statut] || STATUT_CFG.COMMANDER
                  return (
                    <div key={l.id} className="flex items-center gap-3 rounded-xl border border-slate-100 dark:border-slate-700/70 px-4 py-2.5">
                      <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold shrink-0 ${cfg.badge}`}>
                        {cfg.label}
                      </span>
                      <p className="min-w-0 flex-1 truncate text-sm text-slate-800 dark:text-slate-200">{l.designation}</p>
                      <p className="shrink-0 text-sm font-semibold text-slate-900 dark:text-slate-100 tabular-nums">
                        {l.qte_a_commander} u.
                      </p>
                    </div>
                  )
                })}
                {aCommander.length > urgents.length && (
                  <p className="text-xs text-slate-400 dark:text-slate-500 pt-1">
                    + {aCommander.length - urgents.length} autre{aCommander.length - urgents.length > 1 ? 's' : ''} référence{aCommander.length - urgents.length > 1 ? 's' : ''} à commander — voir la liste complète.
                  </p>
                )}
              </div>
            )}
          </div>

          {/* ── À ne pas commander ──────────────────────────────────────── */}
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200/70 dark:border-slate-700/70 p-6">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">À ne pas commander</h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Ces produits n'ont pas besoin d'être réapprovisionnés — en commander reviendrait à immobiliser de l'argent inutilement.
            </p>

            {neSourcePasCommander.length === 0 ? (
              <p className="mt-3 text-sm text-slate-400 dark:text-slate-500">Aucun produit à signaler pour l'instant.</p>
            ) : (
              <>
                <div className="mt-4 rounded-xl bg-danger-light dark:bg-danger/10 border border-danger/20 px-4 py-3">
                  <p className="text-sm font-semibold text-danger">
                    {formatFCFA(totalImmobilise)} immobilisés inutilement au total
                  </p>
                </div>

                <div className="mt-4 space-y-2.5">
                  {neSourcePasCommander.map((l) => (
                    <div key={l.code} className="flex gap-3 rounded-xl border border-slate-100 dark:border-slate-700/70 px-4 py-3">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 truncate">
                          {l.designation} <span className="font-normal text-slate-400 dark:text-slate-500 text-xs">({l.code})</span>
                        </p>
                        <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">{l.motif}</p>
                      </div>
                      <p className="shrink-0 text-sm font-semibold text-danger tabular-nums">
                        {formatFCFA(l.tresorerie_immobilisee)}
                      </p>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </>
      )}
    </div>
  )
}
