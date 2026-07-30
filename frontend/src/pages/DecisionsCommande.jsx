import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import AlerteStrategique from '../components/AlerteStrategique'
import { getListeAction, getANePasCommander } from '../services/dashboard'
import { getEtatImport } from '../services/imports'
import { marquerDirection } from '../services/pageTransition'

function formatFCFA(val) {
  if (!val && val !== 0) return '—'
  return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(val) + ' FCFA'
}

function formatNb(val) {
  return new Intl.NumberFormat('fr-FR').format(val ?? 0)
}

const STATUT_CFG = {
  RUPTURE:   { badge: 'bg-danger text-white',    label: 'Rupture' },
  CRITIQUE:  { badge: 'bg-orange-500 text-white', label: 'Critique' },
  COMMANDER: { badge: 'bg-yellow-400 dark:bg-yellow-500 text-slate-900', label: 'Commander' },
}

export default function DecisionsCommande() {
  const [aCommander, setACommander] = useState([])
  const [neSourcePasCommander, setNePasCommander] = useState([])
  const [etatImport, setEtatImport] = useState(null)
  const [chargement, setChargement] = useState(true)
  const [recherche, setRecherche] = useState('')

  const charger = useCallback(() => {
    return Promise.all([getListeAction(), getANePasCommander(), getEtatImport().catch(() => null)])
      .then(([liste, nePasCommander, etatImport]) => {
        setACommander(liste)
        setNePasCommander(nePasCommander)
        setEtatImport(etatImport)
      })
      .catch(() => {
        setACommander([])
        setNePasCommander([])
      })
      .finally(() => setChargement(false))
  }, [])

  useEffect(() => { charger() }, [charger])

  const q = recherche.trim().toLowerCase()
  const correspond = (l) => l.code?.toLowerCase().includes(q) || l.designation?.toLowerCase().includes(q)

  // En mode ciblé (section 4ter), getListeAction() inclut désormais aussi
  // les références du fichier importé qui n'ont rien à commander (statut
  // OK) — cette section reste centrée sur ce qui est réellement à faire.
  const actionnables = aCommander.filter((l) => l.statut === 'RUPTURE' || l.statut === 'CRITIQUE' || l.statut === 'COMMANDER')

  // Sans recherche : les 8 plus urgentes, comme d'habitude. Avec une
  // recherche, on montre tous les résultats correspondants — plus utile que
  // de rester limité aux 8 premiers pendant qu'on cherche un produit précis.
  const urgents = q
    ? aCommander.filter(correspond)
    : actionnables.filter((l) => l.statut === 'RUPTURE' || l.statut === 'CRITIQUE').slice(0, 8)
  const nePasCommanderFiltre = q ? neSourcePasCommander.filter(correspond) : neSourcePasCommander
  const totalImmobilise = neSourcePasCommander.reduce((s, l) => s + (l.tresorerie_immobilisee || 0), 0)

  return (
    <div className="px-6 py-8 md:px-10 md:py-10 max-w-4xl mx-auto space-y-6">
      <PageHeader
        label="Quoi commander"
        title="Quoi commander ?"
        subtitle="Ce qu'il faut commander en priorité, et ce qu'il ne faut surtout pas recommander."
      />

      <div className="relative w-full sm:w-80">
        <svg viewBox="0 0 20 20" fill="none" className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none">
          <path d="M17.5 17.5l-4.167-4.167M14.167 8.333a5.833 5.833 0 1 1-11.667 0 5.833 5.833 0 0 1 11.667 0Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        </svg>
        <input
          type="text"
          value={recherche}
          onChange={(e) => setRecherche(e.target.value)}
          placeholder="Rechercher un produit ou un code…"
          className="pl-9 pr-4 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 placeholder-slate-400 focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand/30 w-full"
        />
      </div>

      {chargement && <p className="text-sm text-slate-400 dark:text-slate-500">Chargement…</p>}

      {!chargement && etatImport?.mode_commande_ciblee && (
        <div className="rounded-xl bg-info-light dark:bg-info/10 border border-info/30 px-5 py-4">
          <p className="text-sm font-semibold text-info">
            Mode ciblé actif — "À commander en priorité" et "À ne pas commander" ne recherchent que parmi les{' '}
            {formatNb(etatImport.nb_dans_dernier_import)} références de votre dernier import "Préparer ma commande"
          </p>
          <p className="mt-1 text-xs text-info/90">
            L'encart rouge d'alertes stratégiques ci-dessous reste sur l'ensemble du catalogue, volontairement — voir
            l'Aide pour le détail.
          </p>
        </div>
      )}

      {!chargement && (
        <>
          {/* ── Section 7.0 : références stratégiques manquées ──────────── */}
          <AlerteStrategique />

          {/* ── À commander en priorité ─────────────────────────────────── */}
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200/70 dark:border-slate-700/70 p-6">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">À commander en priorité</h2>
              <Link
                to="/liste-action"
                viewTransition
                onClick={() => marquerDirection('/quoi-commander', '/liste-action')}
                className="tg-tap inline-flex items-center gap-1.5 rounded-lg border border-brand px-3 py-1.5 text-xs font-semibold text-brand transition-colors hover:bg-brand-light dark:hover:bg-brand/10"
              >
                Voir la liste complète
                <svg viewBox="0 0 16 16" className="w-3.5 h-3.5" fill="none" aria-hidden="true">
                  <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </Link>
            </div>

            {actionnables.length === 0 ? (
              <p className="mt-3 text-sm text-slate-400 dark:text-slate-500">Rien à commander pour l'instant.</p>
            ) : urgents.length === 0 ? (
              <p className="mt-3 text-sm text-slate-400 dark:text-slate-500">Aucun résultat pour cette recherche.</p>
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
                {!q && actionnables.length > urgents.length && (
                  <p className="text-xs text-slate-400 dark:text-slate-500 pt-1">
                    + {actionnables.length - urgents.length} autre{actionnables.length - urgents.length > 1 ? 's' : ''} référence{actionnables.length - urgents.length > 1 ? 's' : ''} à commander — voir la liste complète.
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
            ) : nePasCommanderFiltre.length === 0 ? (
              <p className="mt-3 text-sm text-slate-400 dark:text-slate-500">Aucun résultat pour cette recherche.</p>
            ) : (
              <>
                <div className="mt-4 rounded-xl bg-danger-light dark:bg-danger/10 border border-danger/20 px-4 py-3">
                  <p className="text-sm font-semibold text-danger">
                    {formatFCFA(totalImmobilise)} immobilisés inutilement au total
                  </p>
                </div>

                <div className="mt-4 space-y-2.5">
                  {nePasCommanderFiltre.map((l) => (
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
