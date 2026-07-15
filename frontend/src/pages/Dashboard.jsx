import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getOfficineNom } from '../services/auth'
import { marquerDirection } from '../services/pageTransition'
import { getKpis, getCommandePlafonnee } from '../services/dashboard'
import ImportHistoryTable from '../components/ImportHistoryTable'
import RepartitionStockDonut from '../components/RepartitionStockDonut'
import VentesM1Table from '../components/VentesM1Table'

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatFCFA(val) {
  if (!val && val !== 0) return '—'
  return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(val) + ' FCFA'
}

function formatDateHeureFr(date) {
  const jour = new Intl.DateTimeFormat('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(date)
  const heure = new Intl.DateTimeFormat('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(date)
  return `${jour} à ${heure}`
}

// ── Sous-composants ───────────────────────────────────────────────────────────

function KpiTile({ label, value, borderColor, badge, iconColor, icon, sousLabel }) {
  return (
    <div className={`group relative overflow-hidden bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200/70 dark:border-slate-700/70 border-l-4 ${borderColor} pl-5 pr-4 py-4 transition-all duration-200 hover:shadow-md hover:-translate-y-0.5`}>
      <span className={`absolute top-3.5 right-3.5 flex h-8 w-8 items-center justify-center rounded-full ${badge} ${iconColor} transition-transform duration-200 group-hover:scale-110`}>
        {icon}
      </span>
      <p className="text-3xl font-extrabold tabular-nums leading-none text-slate-900 dark:text-slate-100">{value}</p>
      <p className="mt-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">{label}</p>
      {sousLabel && (
        <p className="mt-0.5 text-[11px] font-medium text-info">{sousLabel}</p>
      )}
    </div>
  )
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function Dashboard() {
  const navigate = useNavigate()
  const [kpis, setKpis] = useState(null)
  const [plafond, setPlafond] = useState(null)
  const [chargement, setChargement] = useState(true)
  const [maintenant, setMaintenant] = useState(new Date())

  const charger = useCallback(async () => {
    setChargement(true)
    try {
      const [kpis, plafond] = await Promise.all([
        getKpis(),
        getCommandePlafonnee().catch(() => null),
      ])
      setKpis(kpis)
      setPlafond(plafond)
    } catch {
      setKpis(null)
    } finally {
      setChargement(false)
    }
  }, [])

  useEffect(() => { charger() }, [charger])

  useEffect(() => {
    const intervalle = setInterval(() => setMaintenant(new Date()), 1000)
    return () => clearInterval(intervalle)
  }, [])

  function handleImportClick() {
    marquerDirection('/dashboard', '/import')
    navigate('/import', { viewTransition: true })
  }

  const aDesReferences = kpis && kpis.nb_references > 0

  return (
    <div className="px-6 py-8 md:px-10 md:py-10 max-w-6xl mx-auto space-y-6">

      {/* Fil d'ariane + horloge + badge officine */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400 dark:text-slate-500">
        <div className="flex items-center gap-1.5">
          <span>Accueil</span>
          <span>›</span>
          <span className="font-medium text-slate-600 dark:text-slate-300">Tableau de bord</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="tabular-nums capitalize">{formatDateHeureFr(maintenant)}</span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-brand/30 bg-brand-light dark:bg-brand/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-brand-dark dark:text-brand">
            <span className="h-1.5 w-1.5 rounded-full bg-brand" />
            {getOfficineNom()}
          </span>
        </div>
      </div>

      {/* Titre */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">Tableau de bord</h1>
          <p className="mt-1 text-slate-500 dark:text-slate-400 text-sm">Vue d'ensemble de votre stock — StockAid</p>
        </div>
        <button
          onClick={charger}
          className="tg-tap inline-flex items-center gap-2 rounded-lg border border-slate-300 dark:border-slate-600 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 transition-all hover:bg-slate-50 dark:hover:bg-slate-700"
        >
          <svg viewBox="0 0 24 24" fill="none" className={`h-4 w-4 ${chargement ? 'animate-spin' : ''}`} aria-hidden="true">
            <path d="M4 12a8 8 0 0 1 14.13-5.13M20 12a8 8 0 0 1-14.13 5.13M4 4v5h5M20 20v-5h-5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Rafraîchir
        </button>
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
            borderColor="border-l-danger"
            badge="bg-danger-light dark:bg-danger/10"
            iconColor="text-danger"
            icon={<svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true"><path d="M12 9v4m0 4h.01M4.5 19h15a1 1 0 0 0 .87-1.5l-7.5-13a1 1 0 0 0-1.74 0l-7.5 13A1 1 0 0 0 4.5 19Z" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>}
          />
          <KpiTile
            label="Critiques"
            value={kpis.nb_critique}
            borderColor="border-l-orange-500"
            badge="bg-orange-50 dark:bg-orange-500/10"
            iconColor="text-orange-600 dark:text-orange-400"
            icon={<svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true"><path d="M12 7v6m0 4h.01M12 2a10 10 0 1 0 0 20A10 10 0 0 0 12 2Z" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg>}
          />
          <KpiTile
            label="À commander"
            value={kpis.nb_commander}
            borderColor="border-l-amber-500"
            badge="bg-amber-50 dark:bg-amber-500/10"
            iconColor="text-amber-600 dark:text-amber-400"
            icon={<svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true"><path d="M3 3h2l.4 2M7 13h10l3-8H5.4M7 13 5.4 5M7 13l-1.7 3.4A1 1 0 0 0 6.2 18H17M9 21a1 1 0 1 0 0-2 1 1 0 0 0 0 2Zm8 0a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>}
          />
          <KpiTile
            label="Valeur commande"
            value={kpis.valeur_commande_fcfa > 0 ? formatFCFA(kpis.valeur_commande_fcfa) : '—'}
            sousLabel={plafond && !plafond.sans_restriction ? `Plafonnée à ${formatFCFA(plafond.plafond)}` : null}
            borderColor="border-l-info"
            badge="bg-info-light dark:bg-info/10"
            iconColor="text-info"
            icon={<svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true"><path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41M12 7a5 5 0 1 0 0 10A5 5 0 0 0 12 7Z" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg>}
          />
          <KpiTile
            label="Trésorerie libérable"
            value={kpis.tresorerie_liberee_fcfa > 0 ? formatFCFA(kpis.tresorerie_liberee_fcfa) : '—'}
            borderColor="border-l-brand"
            badge="bg-brand-light dark:bg-brand/10"
            iconColor="text-brand-dark dark:text-brand"
            icon={<svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true"><path d="M12 4v16M8 8h5a2 2 0 0 1 0 4H8v-4Zm0 4h6a2 2 0 0 1 0 4H8v-4Z" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>}
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

      {/* ── Ventes du mois dernier, toutes références confondues ────────────── */}
      {!chargement && aDesReferences && <VentesM1Table />}

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
              {aDesReferences ? `Bonjour, ${getOfficineNom()} !` : 'Bienvenue sur StockAid'}
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {aDesReferences
                ? 'Réimportez régulièrement pour maintenir vos recommandations à jour.'
                : 'Importez votre premier fichier pour voir apparaître vos recommandations de commande.'}
            </p>
          </div>
          <button
            onClick={handleImportClick}
            className="tg-tap shrink-0 rounded-xl bg-brand-gradient px-5 py-2.5 font-semibold text-white shadow-sm transition-all hover:shadow-brand hover:-translate-y-0.5"
          >
            {aDesReferences ? 'Importer un nouveau fichier' : 'Importer un fichier'}
          </button>
        </div>
      )}

      {/* ── Historique des imports ────────────────────────────────────────── */}
      <ImportHistoryTable />
    </div>
  )
}
