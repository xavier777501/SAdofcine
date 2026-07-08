import { useEffect, useState, useRef } from 'react'
import { getReferences, updateVed, updateRisque } from '../services/references'

// ── Helpers ──────────────────────────────────────────────────────────────────

function fmtNb(val, dec = 0) {
  if (val == null) return '—'
  return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: dec }).format(val)
}

// ── Constantes ────────────────────────────────────────────────────────────────

const STATUT_CFG = {
  RUPTURE:   { badge: 'bg-danger text-white',                                label: 'Rupture',   row: 'bg-danger-light/40 dark:bg-danger/5' },
  CRITIQUE:  { badge: 'bg-orange-500 text-white',                            label: 'Critique',  row: 'bg-orange-50/60 dark:bg-orange-500/5' },
  COMMANDER: { badge: 'bg-yellow-400 dark:bg-yellow-500 text-slate-900',     label: 'Commander', row: 'bg-yellow-50/60 dark:bg-yellow-500/5' },
  OK:        { badge: 'bg-brand-light dark:bg-brand/10 text-brand-dark dark:text-brand', label: 'OK', row: '' },
}

const CLASSE_CFG = {
  A: 'bg-brand-light text-brand-dark dark:bg-brand/10 dark:text-brand font-bold',
  B: 'bg-info-light text-info dark:bg-info/10 font-bold',
  C: 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400',
}

const FSN_CFG = {
  Fast:        'text-brand dark:text-brand',
  Slow:        'text-orange-500 dark:text-orange-400',
  'Non-moving':'text-slate-400 dark:text-slate-500',
}

const VED_OPTIONS = ['Vital', 'Essentiel', 'Désirable']

// ── Cellule VED éditable ──────────────────────────────────────────────────────

function VedCell({ ligne, onChange, saving }) {
  const canEdit = ligne.classe === 'A' || ligne.classe === 'B'
  const val = ligne.ved || ''

  if (!canEdit) {
    return (
      <span className="text-xs text-slate-400 dark:text-slate-500 italic">
        {val || '—'}
      </span>
    )
  }

  return (
    <div className="relative flex items-center gap-1">
      <select
        value={val}
        disabled={saving}
        onChange={e => onChange(e.target.value || null)}
        className="text-xs rounded-md border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 px-1.5 py-1 pr-5 appearance-none cursor-pointer disabled:opacity-50 focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand/30"
      >
        <option value="">—</option>
        {VED_OPTIONS.map(v => (
          <option key={v} value={v}>{v}</option>
        ))}
      </select>
      {saving
        ? <svg className="w-3 h-3 text-brand animate-spin absolute right-1.5" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity=".25"/><path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/></svg>
        : <svg viewBox="0 0 16 16" fill="none" className="w-3 h-3 text-slate-400 absolute right-1.5 pointer-events-none"><path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
      }
    </div>
  )
}

// ── Cellule Risque fournisseur éditable ───────────────────────────────────────

function RisqueCell({ value, onChange, saving }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(String(value ?? 0))
  const inputRef = useRef(null)

  function startEdit() {
    setDraft(String(value ?? 0))
    setEditing(true)
    setTimeout(() => inputRef.current?.select(), 0)
  }

  function commit() {
    const jours = parseInt(draft, 10)
    if (!isNaN(jours) && jours >= 0 && jours !== value) {
      onChange(jours)
    }
    setEditing(false)
  }

  function onKeyDown(e) {
    if (e.key === 'Enter') commit()
    if (e.key === 'Escape') setEditing(false)
  }

  if (editing) {
    return (
      <input
        ref={inputRef}
        type="number"
        min="0"
        value={draft}
        onChange={e => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={onKeyDown}
        className="w-14 text-xs text-right rounded border border-brand bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-200 px-1.5 py-1 focus:outline-none focus:ring-1 focus:ring-brand/40"
      />
    )
  }

  return (
    <button
      onClick={startEdit}
      disabled={saving}
      title="Cliquer pour modifier"
      className="group flex items-center gap-1 text-xs text-slate-600 dark:text-slate-400 hover:text-brand transition-colors disabled:opacity-50"
    >
      <span className="tabular-nums">{value ?? 0} j</span>
      {saving
        ? <svg className="w-3 h-3 text-brand animate-spin" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity=".25"/><path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/></svg>
        : <svg viewBox="0 0 16 16" fill="none" className="w-3 h-3 opacity-0 group-hover:opacity-60 transition-opacity"><path d="M11 2l3 3-8 8H3v-3L11 2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/></svg>
      }
    </button>
  )
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function Stock() {
  const [refs, setRefs] = useState([])
  const [chargement, setChargement] = useState(true)
  const [recherche, setRecherche] = useState('')
  const [filtreStatut, setFiltreStatut] = useState('TOUS')
  const [filtreClasse, setFiltreClasse] = useState('TOUS')
  // savingId → 'ved' | 'risque' | null
  const [saving, setSaving] = useState({})

  useEffect(() => {
    const ctrl = new AbortController()
    setChargement(true)
    getReferences(ctrl.signal)
      .then(data => setRefs(data))
      .catch(() => { if (!ctrl.signal.aborted) setRefs([]) })
      .finally(() => { if (!ctrl.signal.aborted) setChargement(false) })
    return () => ctrl.abort()
  }, [])

  async function handleVedChange(ref, ved) {
    setSaving(s => ({ ...s, [ref.id]: 'ved' }))
    try {
      const updated = await updateVed(ref.id, ved)
      setRefs(prev => prev.map(r => r.id === updated.id ? { ...r, ...updated } : r))
    } catch { /* silencieux */ }
    finally { setSaving(s => { const n = { ...s }; delete n[ref.id]; return n }) }
  }

  async function handleRisqueChange(ref, jours) {
    setSaving(s => ({ ...s, [ref.id]: 'risque' }))
    try {
      const updated = await updateRisque(ref.id, jours)
      setRefs(prev => prev.map(r => r.id === updated.id ? { ...r, ...updated } : r))
    } catch { /* silencieux */ }
    finally { setSaving(s => { const n = { ...s }; delete n[ref.id]; return n }) }
  }

  // Filtres
  const query = recherche.toLowerCase()
  const refsFiltrees = refs.filter(r => {
    if (filtreStatut !== 'TOUS' && r.statut !== filtreStatut) return false
    if (filtreClasse !== 'TOUS' && r.classe !== filtreClasse) return false
    if (query && !r.code?.toLowerCase().includes(query) && !r.designation?.toLowerCase().includes(query)) return false
    return true
  })

  const nbParStatut = s => refs.filter(r => r.statut === s).length

  return (
    <div className="px-6 py-8 md:px-10 md:py-10 max-w-7xl mx-auto space-y-5">

      {/* Titre */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">Stock</h1>
        <p className="mt-1 text-slate-500 dark:text-slate-400 text-sm">
          {chargement ? 'Chargement…' : `${refs.length} référence${refs.length > 1 ? 's' : ''} — ${refsFiltrees.length} affichée${refsFiltrees.length > 1 ? 's' : ''}`}
        </p>
      </div>

      {/* Barre de filtres */}
      <div className="flex flex-wrap gap-3 items-center">
        {/* Recherche */}
        <div className="relative">
          <svg viewBox="0 0 20 20" fill="none" className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none">
            <path d="M17.5 17.5l-4.167-4.167M14.167 8.333a5.833 5.833 0 1 1-11.667 0 5.833 5.833 0 0 1 11.667 0Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
          <input
            type="text"
            value={recherche}
            onChange={e => setRecherche(e.target.value)}
            placeholder="Rechercher code ou désignation…"
            className="pl-9 pr-4 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 placeholder-slate-400 focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand/30 w-72"
          />
        </div>

        {/* Filtre statut */}
        <div className="flex gap-1.5 flex-wrap">
          {['TOUS', 'RUPTURE', 'CRITIQUE', 'COMMANDER', 'OK'].map(s => {
            const cfg = STATUT_CFG[s]
            const actif = filtreStatut === s
            return (
              <button
                key={s}
                onClick={() => setFiltreStatut(s)}
                className={`tg-tap text-xs font-medium px-3 py-1.5 rounded-full border transition-all ${
                  actif
                    ? s === 'TOUS' ? 'bg-slate-800 dark:bg-slate-200 text-white dark:text-slate-900 border-transparent' : `${cfg.badge} border-transparent`
                    : 'bg-white dark:bg-slate-800 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-600 hover:border-slate-300'
                }`}
              >
                {s === 'TOUS' ? 'Tous' : cfg.label}
                {s !== 'TOUS' && <span className="ml-1 opacity-70">{nbParStatut(s)}</span>}
              </button>
            )
          })}
        </div>

        {/* Filtre classe */}
        <div className="flex gap-1.5">
          {['TOUS', 'A', 'B', 'C'].map(c => (
            <button
              key={c}
              onClick={() => setFiltreClasse(c)}
              className={`tg-tap text-xs font-bold px-2.5 py-1.5 rounded-lg border transition-all ${
                filtreClasse === c
                  ? c === 'TOUS' ? 'bg-slate-800 dark:bg-slate-200 text-white dark:text-slate-900 border-transparent' : `${CLASSE_CFG[c]} border-transparent`
                  : 'bg-white dark:bg-slate-800 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-600 hover:border-slate-300'
              }`}
            >
              {c === 'TOUS' ? 'Cl. tous' : `Classe ${c}`}
            </button>
          ))}
        </div>
      </div>

      {chargement && (
        <div className="flex items-center gap-3 text-slate-400 text-sm py-10">
          <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity=".25"/>
            <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
          </svg>
          Chargement des références…
        </div>
      )}

      {/* Tableau */}
      {!chargement && (
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200/70 dark:border-slate-700/70 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm" style={{ minWidth: '1020px' }}>
              <thead>
                <tr className="text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide border-b border-slate-100 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-700/30">
                  <th className="px-4 py-3">Statut</th>
                  <th className="px-4 py-3">Code</th>
                  <th className="px-4 py-3">Désignation</th>
                  <th className="px-4 py-3 text-center">Cl.</th>
                  <th className="px-4 py-3 text-center">FSN</th>
                  <th className="px-4 py-3">VED</th>
                  <th className="px-4 py-3 text-right">Stock</th>
                  <th className="px-4 py-3 text-right">CMM</th>
                  <th className="px-4 py-3 text-right">SS</th>
                  <th className="px-4 py-3 text-right">PC</th>
                  <th className="px-4 py-3 text-right">Qté cmd.</th>
                  <th className="px-4 py-3 text-right">Risque frs.</th>
                </tr>
              </thead>
              <tbody>
                {refsFiltrees.length === 0 ? (
                  <tr>
                    <td colSpan={12} className="px-4 py-10 text-center text-slate-400 dark:text-slate-500 text-sm">
                      Aucune référence pour ces filtres.
                    </td>
                  </tr>
                ) : (
                  refsFiltrees.map(r => {
                    const statCfg = STATUT_CFG[r.statut] || STATUT_CFG.OK
                    const isSaving = !!saving[r.id]
                    return (
                      <tr
                        key={r.id}
                        className={`border-b border-slate-100 dark:border-slate-700/50 last:border-0 transition-colors hover:bg-slate-50/80 dark:hover:bg-slate-700/20 ${statCfg.row}`}
                      >
                        {/* Statut */}
                        <td className="px-4 py-2.5 whitespace-nowrap">
                          <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${statCfg.badge}`}>
                            {statCfg.label}
                          </span>
                        </td>
                        {/* Code */}
                        <td className="px-4 py-2.5 font-mono text-xs text-slate-600 dark:text-slate-300 whitespace-nowrap">
                          {r.code}
                        </td>
                        {/* Désignation */}
                        <td className="px-4 py-2.5 max-w-[220px]">
                          <p className="line-clamp-1 text-sm text-slate-800 dark:text-slate-200" title={r.designation}>
                            {r.designation}
                          </p>
                          {r.forme && (
                            <p className="text-xs text-slate-400 dark:text-slate-500 line-clamp-1">{r.forme}</p>
                          )}
                        </td>
                        {/* Classe */}
                        <td className="px-4 py-2.5 text-center">
                          {r.classe && (
                            <span className={`inline-block rounded-md px-2 py-0.5 text-xs ${CLASSE_CFG[r.classe] || ''}`}>
                              {r.classe}
                            </span>
                          )}
                        </td>
                        {/* FSN */}
                        <td className="px-4 py-2.5 text-center">
                          <span className={`text-xs font-medium ${FSN_CFG[r.fsn] || 'text-slate-500'}`}>
                            {r.fsn || '—'}
                          </span>
                        </td>
                        {/* VED éditable */}
                        <td className="px-4 py-2.5">
                          <VedCell
                            ligne={r}
                            saving={saving[r.id] === 'ved'}
                            onChange={ved => handleVedChange(r, ved)}
                          />
                        </td>
                        {/* Stock */}
                        <td className="px-4 py-2.5 text-right tabular-nums text-sm text-slate-700 dark:text-slate-300">
                          {fmtNb(r.stock_actuel)}
                        </td>
                        {/* CMM */}
                        <td className="px-4 py-2.5 text-right tabular-nums text-xs text-slate-500 dark:text-slate-400">
                          {fmtNb(r.cmm, 1)}
                        </td>
                        {/* SS */}
                        <td className="px-4 py-2.5 text-right tabular-nums text-xs text-slate-500 dark:text-slate-400">
                          {fmtNb(r.ss, 1)}
                        </td>
                        {/* PC */}
                        <td className="px-4 py-2.5 text-right tabular-nums text-xs text-slate-500 dark:text-slate-400">
                          {fmtNb(r.pc, 1)}
                        </td>
                        {/* Qté à commander */}
                        <td className="px-4 py-2.5 text-right tabular-nums text-sm font-semibold text-slate-800 dark:text-slate-200">
                          {r.qte_a_commander > 0 ? fmtNb(r.qte_a_commander) : '—'}
                        </td>
                        {/* Risque fournisseur éditable */}
                        <td className="px-4 py-2.5 text-right">
                          <RisqueCell
                            value={r.risque_fournisseur_jours}
                            saving={saving[r.id] === 'risque'}
                            onChange={jours => handleRisqueChange(r, jours)}
                          />
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Pied de tableau */}
          {refsFiltrees.length > 0 && (
            <div className="px-6 py-3 border-t border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-700/20 text-xs text-slate-400 dark:text-slate-500">
              {refsFiltrees.length} référence{refsFiltrees.length > 1 ? 's' : ''} affichée{refsFiltrees.length > 1 ? 's' : ''}
              {filtreStatut !== 'TOUS' || filtreClasse !== 'TOUS' || recherche
                ? ` sur ${refs.length} au total`
                : ''}
              {' · '}VED modifiable uniquement pour les classes A et B
              {' · '}Cliquer sur le risque fournisseur pour modifier
            </div>
          )}
        </div>
      )}
    </div>
  )
}
