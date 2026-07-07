import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getOfficineNom } from '../services/auth'
import { marquerDirection } from '../services/pageTransition'
import { getKpis, getListeAction, exportListe } from '../services/dashboard'
import ImportHistoryTable from '../components/ImportHistoryTable'
import RepartitionStockDonut from '../components/RepartitionStockDonut'

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatFCFA(val) {
  if (!val && val !== 0) return '—'
  return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(val) + ' FCFA'
}

function formatNb(val) {
  return new Intl.NumberFormat('fr-FR').format(val ?? 0)
}

// ── Constantes de statut ─────────────────────────────────────────────────────

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

// ── Sous-composants ───────────────────────────────────────────────────────────

function KpiTile({ label, value, sub, color, icon }) {
  return (
    <div className={`group bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200/70 dark:border-slate-700/70 px-5 py-4 flex items-center gap-4 transition-all duration-200 hover:shadow-md hover:-translate-y-0.5`}>
      <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${color} transition-transform duration-200 group-hover:scale-110`}>
        {icon}
      </span>
      <div className="min-w-0">
        <p className="text-xs text-slate-500 dark:text-slate-400 leading-tight">{label}</p>
        <p className={`text-2xl font-bold tabular-nums leading-tight ${color.replace(/bg-\S+/, '').trim()}`}>{value}</p>
        {sub && <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
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
          <td colSpan={8} className="px-4 py-2.5">
            <p className={`text-sm font-medium italic ${cfg.text}`}>{ligne.texte_decision}</p>
          </td>
        </tr>
      )}
    </>
  )
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function Dashboard() {
  const navigate = useNavigate()
  const [kpis, setKpis] = useState(null)
  const [liste, setListe] = useState([])
  const [chargement, setChargement] = useState(true)
  const [exportEnCours, setExportEnCours] = useState(null)
  const [ligneOuverte, setLigneOuverte] = useState(null)
  const [filtreStatut, setFiltreStatut] = useState('TOUS')

  const charger = useCallback(async () => {
    setChargement(true)
    try {
      const [k, l] = await Promise.all([getKpis(), getListeAction()])
      setKpis(k)
      setListe(l)
    } catch {
      setKpis(null)
      setListe([])
    } finally {
      setChargement(false)
    }
  }, [])

  useEffect(() => { charger() }, [charger])

  async function handleExport(format) {
    setExportEnCours(format)
    try { await exportListe(format) } catch { /* silencieux */ } finally { setExportEnCours(null) }
  }

  function handleImportClick() {
    marquerDirection('/dashboard', '/import')
    navigate('/import', { viewTransition: true })
  }

  const aDesReferences = kpis && kpis.nb_a_commander + (kpis.nb_references ?? 0) > 0
  const listeFiltre = filtreStatut === 'TOUS' ? liste : liste.filter(l => l.statut === filtreStatut)

  return (
    <div className="px-6 py-8 md:px-10 md:py-10 max-w-6xl mx-auto space-y-6">

      {/* Titre */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">Tableau de bord</h1>
        <p className="mt-1 text-slate-500 dark:text-slate-400 text-sm">{getOfficineNom()}</p>
      </div>

      {chargement && (
        <div className="flex items-center gap-3 text-slate-400 dark:text-slate-500 text-sm py-8">
          <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity=".25"/>
            <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
          </svg>
          Chargement des données…
        </div>
      )}

      {/* ── KPIs 5 tuiles ─────────────────────────────────────────────────── */}
      {!chargement && kpis && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <KpiTile
            label="En rupture"
            value={kpis.nb_rupture}
            color="bg-danger-light dark:bg-danger/10 text-danger"
            icon={<svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true"><path d="M12 9v4m0 4h.01M4.5 19h15a1 1 0 0 0 .87-1.5l-7.5-13a1 1 0 0 0-1.74 0l-7.5 13A1 1 0 0 0 4.5 19Z" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>}
          />
          <KpiTile
            label="Critiques"
            value={kpis.nb_critique}
            color="bg-orange-50 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400"
            icon={<svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true"><path d="M12 7v6m0 4h.01M12 2a10 10 0 1 0 0 20A10 10 0 0 0 12 2Z" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg>}
          />
          <KpiTile
            label="À commander"
            value={kpis.nb_a_commander}
            color="bg-yellow-50 dark:bg-yellow-500/10 text-yellow-700 dark:text-yellow-400"
            icon={<svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true"><path d="M3 3h2l.4 2M7 13h10l3-8H5.4M7 13 5.4 5M7 13l-1.7 3.4A1 1 0 0 0 6.2 18H17M9 21a1 1 0 1 0 0-2 1 1 0 0 0 0 2Zm8 0a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>}
          />
          <KpiTile
            label="Valeur commande"
            value={kpis.valeur_commande_fcfa > 0 ? formatFCFA(kpis.valeur_commande_fcfa) : '—'}
            color="bg-info-light dark:bg-info/10 text-info"
            icon={<svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true"><path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41M12 7a5 5 0 1 0 0 10A5 5 0 0 0 12 7Z" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg>}
          />
          <KpiTile
            label="Trésorerie libérable"
            value={kpis.tresorerie_liberee_fcfa > 0 ? formatFCFA(kpis.tresorerie_liberee_fcfa) : '—'}
            sub="Stock excédentaire"
            color="bg-brand-light dark:bg-brand/10 text-brand-dark dark:text-brand"
            icon={<svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true"><path d="M12 4v16M8 8h5a2 2 0 0 1 0 4H8v-4Zm0 4h6a2 2 0 0 1 0 4H8v-4Z" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>}
          />
        </div>
      )}

      {/* ── Anneau de répartition ──────────────────────────────────────────── */}
      {!chargement && kpis && kpis.nb_a_commander > 0 && (
        <RepartitionStockDonut
          nbRupture={kpis.nb_rupture}
          nbACommander={kpis.nb_a_commander}
          nbReferences={kpis.nb_references}
        />
      )}

      {/* ── Liste d'action ─────────────────────────────────────────────────── */}
      {!chargement && liste.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200/70 dark:border-slate-700/70 overflow-hidden">

          {/* En-tête de section */}
          <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-4 border-b border-slate-100 dark:border-slate-700">
            <div>
              <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                Liste d'action
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                {liste.length} référence{liste.length > 1 ? 's' : ''} à traiter — cliquez sur une ligne pour voir le conseil
              </p>
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              {/* Filtres statut */}
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

              {/* Export */}
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

          {/* Tableau */}
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

      {/* ── État vide / CTA import ────────────────────────────────────────── */}
      {!chargement && (
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200/70 dark:border-slate-700/70 px-8 py-7 flex flex-col md:flex-row items-center gap-6 transition-all duration-200 hover:shadow-md hover:-translate-y-0.5">
          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-brand-light dark:bg-brand/10">
            <svg viewBox="0 0 24 24" fill="none" className="h-7 w-7 text-brand" aria-hidden="true">
              <path d="M12 4v10m0 0-3.5-3.5M12 14l3.5-3.5M5 17v1.5A1.5 1.5 0 0 0 6.5 20h11a1.5 1.5 0 0 0 1.5-1.5V17" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div className="flex-1 text-center md:text-left">
            <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
              {liste.length > 0 ? `Bonjour, ${getOfficineNom()} !` : 'Bienvenue sur StockAid'}
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {liste.length > 0
                ? 'Réimportez régulièrement pour maintenir vos recommandations à jour.'
                : 'Importez votre premier fichier pour voir apparaître vos recommandations de commande.'}
            </p>
          </div>
          <button
            onClick={handleImportClick}
            className="tg-tap shrink-0 rounded-xl bg-brand-gradient px-5 py-2.5 font-semibold text-white shadow-sm transition-all hover:shadow-brand hover:-translate-y-0.5"
          >
            {liste.length > 0 ? 'Importer un nouveau fichier' : 'Importer un fichier'}
          </button>
        </div>
      )}

      {/* ── Historique des imports ────────────────────────────────────────── */}
      <ImportHistoryTable />
    </div>
  )
}
