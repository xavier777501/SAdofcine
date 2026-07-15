import { useEffect, useState, useCallback } from 'react'
import { getListeAction, exportListe, getCommandePlafonnee } from '../services/dashboard'
import PageHeader from '../components/PageHeader'

function formatFCFA(val) {
  if (!val && val !== 0) return '—'
  return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(val) + ' FCFA'
}

function formatNb(val) {
  return new Intl.NumberFormat('fr-FR').format(val ?? 0)
}

const STATUT_CFG = {
  RUPTURE:   { bg: 'bg-danger-light dark:bg-danger/10',   text: 'text-danger',                    badge: 'bg-danger text-white',                        label: 'Rupture' },
  CRITIQUE:  { bg: 'bg-orange-50 dark:bg-orange-500/10', text: 'text-orange-600 dark:text-orange-400', badge: 'bg-orange-500 text-white',               label: 'Critique' },
  COMMANDER: { bg: 'bg-yellow-50 dark:bg-yellow-500/10', text: 'text-yellow-700 dark:text-yellow-400', badge: 'bg-yellow-400 dark:bg-yellow-500 text-slate-900', label: 'Commander' },
}

const CLASSE_CFG = {
  A: 'bg-brand-light text-brand-dark dark:bg-brand/10 dark:text-brand',
  B: 'bg-info-light text-info dark:bg-info/10',
  C: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
}

function LigneAction({ ligne, expanded, onToggle }) {
  const cfg = STATUT_CFG[ligne.statut] || {}
  const classeCfg = CLASSE_CFG[ligne.classe] || CLASSE_CFG.C

  return (
    <>
      <tr
        className={`border-b border-slate-100 dark:border-slate-700/50 cursor-pointer transition-colors ${expanded ? cfg.bg : 'hover:bg-slate-50 dark:hover:bg-slate-700/30'}`}
        onClick={onToggle}
      >
        <td className="px-4 py-2.5">
          <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${cfg.badge}`}>
            {cfg.label}
          </span>
        </td>
        <td className="px-4 py-2.5 font-mono text-xs text-slate-600 dark:text-slate-300 whitespace-nowrap">
          {ligne.code}
        </td>
        <td className="px-4 py-2.5 text-sm text-slate-800 dark:text-slate-200 max-w-xs">
          <span className="line-clamp-1">{ligne.designation}</span>
        </td>
        <td className="px-4 py-2.5 text-center">
          {ligne.classe && (
            <span className={`inline-block rounded-md px-2 py-0.5 text-xs font-bold ${classeCfg}`}>
              {ligne.classe}
            </span>
          )}
        </td>
        <td className="px-4 py-2.5 text-right tabular-nums text-sm text-slate-600 dark:text-slate-400">
          {formatNb(ligne.stock_actuel)}
        </td>
        <td className="px-4 py-2.5 text-right tabular-nums text-sm font-semibold text-slate-800 dark:text-slate-200">
          {formatNb(ligne.qte_a_commander)}
        </td>
        <td className="px-4 py-2.5 text-right tabular-nums text-sm text-slate-600 dark:text-slate-400">
          {ligne.valeur_fcfa > 0 ? formatFCFA(ligne.valeur_fcfa) : '—'}
        </td>
        <td className="px-4 py-2.5 text-center w-8">
          <svg viewBox="0 0 16 16" className={`w-4 h-4 text-slate-400 transition-transform duration-200 inline ${expanded ? 'rotate-180' : ''}`} fill="none">
            <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </td>
      </tr>
      {expanded && (
        <tr className={cfg.bg}>
          <td colSpan={8} className="px-4 py-2.5 space-y-1">
            <p className={`text-sm font-medium italic ${cfg.text}`}>{ligne.texte_decision}</p>
            {ligne.sorties_derniere_commande != null && (
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {formatNb(ligne.sorties_derniere_commande)} unité{ligne.sorties_derniere_commande > 1 ? 's' : ''} vendue{ligne.sorties_derniere_commande > 1 ? 's' : ''} depuis la dernière commande
              </p>
            )}
          </td>
        </tr>
      )}
    </>
  )
}

function LignePlafond({ ligne, reportee }) {
  const cfg = STATUT_CFG[ligne.statut] || {}
  const classeCfg = CLASSE_CFG[ligne.classe] || CLASSE_CFG.C

  return (
    <tr className={`border-b border-slate-100 dark:border-slate-700/50 ${reportee ? 'opacity-50' : ''}`}>
      <td className="px-4 py-2.5">
        <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${cfg.badge}`}>
          {cfg.label}
        </span>
        {ligne.hors_plafond && (
          <span className="ml-1.5 inline-block rounded-full px-2 py-0.5 text-[10px] font-bold bg-danger text-white">
            HORS PLAFOND
          </span>
        )}
      </td>
      <td className="px-4 py-2.5 font-mono text-xs text-slate-600 dark:text-slate-300 whitespace-nowrap">
        {ligne.code}
      </td>
      <td className="px-4 py-2.5 text-sm text-slate-800 dark:text-slate-200 max-w-xs">
        <span className="line-clamp-1">{ligne.designation}</span>
      </td>
      <td className="px-4 py-2.5 text-center">
        {ligne.classe && (
          <span className={`inline-block rounded-md px-2 py-0.5 text-xs font-bold ${classeCfg}`}>
            {ligne.classe}
          </span>
        )}
      </td>
      <td className="px-4 py-2.5 text-right tabular-nums text-sm text-slate-600 dark:text-slate-400">
        {formatNb(ligne.stock_actuel)}
      </td>
      <td className="px-4 py-2.5 text-right tabular-nums text-sm font-semibold text-slate-800 dark:text-slate-200">
        {formatNb(ligne.qte_a_commander)}
      </td>
      <td className="px-4 py-2.5 text-right tabular-nums text-sm text-slate-600 dark:text-slate-400">
        {ligne.valeur_fcfa > 0 ? formatFCFA(ligne.valeur_fcfa) : '—'}
      </td>
    </tr>
  )
}

export default function ListeAction() {
  const [liste, setListe] = useState([])
  const [plafond, setPlafond] = useState(null)
  const [chargement, setChargement] = useState(true)
  const [exportEnCours, setExportEnCours] = useState(null)
  const [ligneOuverte, setLigneOuverte] = useState(null)
  const [filtreStatut, setFiltreStatut] = useState('TOUS')

  const charger = useCallback(async () => {
    setChargement(true)
    try {
      const [liste, plafond] = await Promise.all([
        getListeAction(),
        getCommandePlafonnee().catch(() => null),
      ])
      setListe(liste)
      setPlafond(plafond)
    } catch {
      setListe([])
    } finally {
      setChargement(false)
    }
  }, [])

  useEffect(() => { charger() }, [charger])

  const plafondActif = plafond && !plafond.sans_restriction

  async function handleExport(format) {
    setExportEnCours(format)
    try { await exportListe(format) } catch { /* silencieux */ } finally { setExportEnCours(null) }
  }

  const listeFiltre = filtreStatut === 'TOUS' ? liste : liste.filter(l => l.statut === filtreStatut)

  return (
    <div className="px-6 py-8 md:px-10 md:py-10 max-w-6xl mx-auto space-y-6">
      <PageHeader
        label="Liste d'action"
        title="Liste d'action"
        subtitle="Références à traiter, triées par urgence — cliquez sur une ligne pour voir le conseil"
      />

      {!chargement && plafondActif && (
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200/70 dark:border-slate-700/70 p-5 space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
              Budget utilisé : {formatFCFA(plafond.budget_utilise)} / {formatFCFA(plafond.plafond)}
            </p>
            {plafond.montant_reporte > 0 && (
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {formatFCFA(plafond.montant_reporte)} reportés à la prochaine commande
              </p>
            )}
          </div>
          <div className="h-2 w-full bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-brand rounded-full transition-all"
              style={{ width: `${Math.min(100, (plafond.budget_utilise / plafond.plafond) * 100)}%` }}
            />
          </div>
          {plafond.rupture_non_vitale_reportee && (
            <p className="text-xs font-medium text-danger">
              Attention : des références en rupture sont reportées faute de budget — pensez à arbitrer manuellement.
            </p>
          )}
        </div>
      )}

      {chargement && (
        <div className="flex items-center gap-3 text-slate-400 dark:text-slate-500 text-sm py-8">
          <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity=".25"/>
            <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
          </svg>
          Chargement des données…
        </div>
      )}

      {!chargement && liste.length === 0 && (
        <p className="text-sm text-slate-400 dark:text-slate-500 py-8 text-center">
          Aucune référence à traiter pour le moment.
        </p>
      )}

      {!chargement && plafondActif && (
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200/70 dark:border-slate-700/70 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[720px]">
              <thead>
                <tr className="text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide border-b border-slate-100 dark:border-slate-700">
                  <th className="px-4 py-2.5">Statut</th>
                  <th className="px-4 py-2.5">Code</th>
                  <th className="px-4 py-2.5">Désignation</th>
                  <th className="px-4 py-2.5 text-center">Cl.</th>
                  <th className="px-4 py-2.5 text-right">Stock</th>
                  <th className="px-4 py-2.5 text-right">Qté à cmd.</th>
                  <th className="px-4 py-2.5 text-right">Valeur</th>
                </tr>
              </thead>
              <tbody>
                {plafond.hors_plafond.map((ligne) => (
                  <LignePlafond key={ligne.id} ligne={ligne} />
                ))}
                {plafond.inclus.map((ligne) => (
                  <LignePlafond key={ligne.id} ligne={ligne} />
                ))}
                {plafond.reporte.length > 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-2 bg-slate-50 dark:bg-slate-900/40 text-xs font-semibold text-slate-500 dark:text-slate-400 text-center border-y border-slate-200 dark:border-slate-700">
                      ↓ Reportées à la prochaine commande — plafond atteint ({formatFCFA(plafond.montant_reporte)}) ↓
                    </td>
                  </tr>
                )}
                {plafond.reporte.map((ligne) => (
                  <LignePlafond key={ligne.id} ligne={ligne} reportee />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!chargement && !plafondActif && liste.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200/70 dark:border-slate-700/70 overflow-hidden">

          <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-4 border-b border-slate-100 dark:border-slate-700">
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {liste.length} référence{liste.length > 1 ? 's' : ''} à traiter
            </p>

            <div className="flex items-center gap-2 flex-wrap">
              {['TOUS', 'RUPTURE', 'CRITIQUE', 'COMMANDER'].map(s => {
                const cfg = STATUT_CFG[s]
                const actif = filtreStatut === s
                return (
                  <button
                    key={s}
                    onClick={() => setFiltreStatut(s)}
                    className={`tg-tap text-xs font-medium px-3 py-1.5 rounded-full border transition-all ${
                      actif
                        ? s === 'TOUS'
                          ? 'bg-slate-800 dark:bg-slate-200 text-white dark:text-slate-900 border-transparent'
                          : `${cfg.badge} border-transparent`
                        : 'bg-transparent text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-600 hover:border-slate-300'
                    }`}
                  >
                    {s === 'TOUS' ? 'Tous' : cfg.label}
                    {s !== 'TOUS' && (
                      <span className="ml-1.5 opacity-70">
                        {liste.filter(l => l.statut === s).length}
                      </span>
                    )}
                  </button>
                )
              })}

              <div className="flex gap-2 ml-2">
                <button
                  onClick={() => handleExport('xlsx')}
                  disabled={!!exportEnCours}
                  className="tg-tap flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg border border-brand text-brand hover:bg-brand-light dark:hover:bg-brand/10 transition-colors disabled:opacity-50"
                >
                  <svg viewBox="0 0 16 16" className="w-3.5 h-3.5" fill="none" aria-hidden="true">
                    <path d="M8 1v9M5 7l3 3 3-3M2 11v2a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  {exportEnCours === 'xlsx' ? 'Export…' : 'Excel'}
                </button>
                <button
                  onClick={() => handleExport('pdf')}
                  disabled={!!exportEnCours}
                  className="tg-tap flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50"
                >
                  <svg viewBox="0 0 16 16" className="w-3.5 h-3.5" fill="none" aria-hidden="true">
                    <path d="M8 1v9M5 7l3 3 3-3M2 11v2a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  {exportEnCours === 'pdf' ? 'Export…' : 'PDF'}
                </button>
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[720px]">
              <thead>
                <tr className="text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide border-b border-slate-100 dark:border-slate-700">
                  <th className="px-4 py-2.5">Statut</th>
                  <th className="px-4 py-2.5">Code</th>
                  <th className="px-4 py-2.5">Désignation</th>
                  <th className="px-4 py-2.5 text-center">Cl.</th>
                  <th className="px-4 py-2.5 text-right">Stock</th>
                  <th className="px-4 py-2.5 text-right">Qté à cmd.</th>
                  <th className="px-4 py-2.5 text-right">Valeur</th>
                  <th className="px-4 py-2.5 w-8"></th>
                </tr>
              </thead>
              <tbody>
                {listeFiltre.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center text-slate-400 dark:text-slate-500 text-sm">
                      Aucune référence pour ce filtre.
                    </td>
                  </tr>
                ) : (
                  listeFiltre.map(ligne => (
                    <LigneAction
                      key={ligne.id}
                      ligne={ligne}
                      expanded={ligneOuverte === ligne.id}
                      onToggle={() => setLigneOuverte(prev => prev === ligne.id ? null : ligne.id)}
                    />
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
