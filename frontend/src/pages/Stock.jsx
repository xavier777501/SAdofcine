import { useEffect, useState, useRef } from 'react'
import { getReferences, updateVed, updateRisque, updateAjustementCommande } from '../services/references'
import { estNeutralise, MESSAGE_NEUTRALISE } from '../utils/recommandation'
import PageHeader from '../components/PageHeader'

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

// Libellés en langage clair (le jargon FSN/VED/CMM/SS/PC ne doit jamais
// s'afficher au pharmacien — cahier des charges section 9).
const ROTATION_CFG = {
  Fast:        { classe: 'text-brand dark:text-brand',                 label: 'Rapide' },
  Slow:        { classe: 'text-orange-500 dark:text-orange-400',       label: 'Lente' },
  'Non-moving':{ classe: 'text-slate-400 dark:text-slate-500',         label: 'Rare' },
}

const VED_OPTIONS = ['Vital', 'Essentiel', 'Désirable']

// ── Liste déroulante de filtre, intégrée directement dans l'en-tête de
// colonne (comme les filtres de colonne d'un tableur, terrain connu des
// pharmaciens qui utilisaient Excel) ────────────────────────────────────────
function ThFiltre({ label, value, onChange, options, align = 'left' }) {
  return (
    <th className={`px-4 py-2.5 ${align === 'center' ? 'text-center' : align === 'right' ? 'text-right' : ''}`}>
      <div className={`flex flex-col gap-1 ${align === 'center' ? 'items-center' : align === 'right' ? 'items-end' : 'items-start'}`}>
        <span>{label}</span>
        <div className="relative">
          <select
            value={value}
            onChange={e => onChange(e.target.value)}
            className="normal-case text-[11px] font-medium rounded-md border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 pl-2 pr-5 py-1 appearance-none cursor-pointer focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand/30"
          >
            {options.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <svg viewBox="0 0 16 16" fill="none" className="w-2.5 h-2.5 text-slate-400 absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none"><path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
        </div>
      </div>
    </th>
  )
}

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

// ── Cellule arbitrage manuel (section 6.7) ────────────────────────────────────

function CommandeCell({ ligne, onChange, saving }) {
  if (ligne.inclusion_manuelle === 'exclure') {
    return (
      <button
        onClick={() => onChange(null)}
        disabled={saving}
        title="Cette référence a été exclue manuellement de la prochaine commande"
        className="tg-tap inline-flex items-center gap-1 rounded-full border border-slate-300 dark:border-slate-600 px-2 py-0.5 text-[11px] font-medium text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50"
      >
        Exclue{saving ? '…' : ' · réinclure'}
      </button>
    )
  }
  if (ligne.inclusion_manuelle === 'inclure') {
    return (
      <button
        onClick={() => onChange(null)}
        disabled={saving}
        title="Cette référence a été ajoutée manuellement à la prochaine commande"
        className="tg-tap inline-flex items-center gap-1 rounded-full border border-info/40 px-2 py-0.5 text-[11px] font-medium text-info hover:bg-info-light dark:hover:bg-info/10 disabled:opacity-50"
      >
        Forcée{saving ? '…' : ' · annuler'}
      </button>
    )
  }
  if (ligne.statut === 'OK') {
    return (
      <button
        onClick={() => onChange('inclure')}
        disabled={saving}
        title="Commander cette référence quand même, même si le stock est suffisant"
        className="tg-tap rounded-full border border-slate-200 dark:border-slate-600 px-2 py-0.5 text-[11px] font-medium text-slate-400 dark:text-slate-500 hover:border-brand hover:text-brand disabled:opacity-50"
      >
        {saving ? '…' : '+ Ajouter'}
      </button>
    )
  }
  return <span className="text-xs text-slate-300 dark:text-slate-600">—</span>
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function Stock() {
  const [refs, setRefs] = useState([])
  const [chargement, setChargement] = useState(true)
  const [recherche, setRecherche] = useState('')
  const [filtreStatut, setFiltreStatut] = useState('TOUS')
  const [filtreClasse, setFiltreClasse] = useState('TOUS')
  const [filtreRotation, setFiltreRotation] = useState('TOUS')
  const [filtrePriorite, setFiltrePriorite] = useState('TOUS')
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

  async function handleCommandeChange(ref, inclusionManuelle) {
    setSaving(s => ({ ...s, [ref.id]: 'commande' }))
    try {
      const updated = await updateAjustementCommande(ref.id, {
        qteOverride: ref.qte_a_commander_override,
        inclusionManuelle,
      })
      setRefs(prev => prev.map(r => r.id === updated.id ? { ...r, ...updated } : r))
    } catch { /* silencieux */ }
    finally { setSaving(s => { const n = { ...s }; delete n[ref.id]; return n }) }
  }

  // Filtres
  const query = recherche.toLowerCase()
  const refsFiltrees = refs.filter(r => {
    if (filtreStatut !== 'TOUS' && r.statut !== filtreStatut) return false
    if (filtreClasse !== 'TOUS' && r.classe !== filtreClasse) return false
    if (filtreRotation !== 'TOUS' && r.fsn !== filtreRotation) return false
    if (filtrePriorite !== 'TOUS' && (r.ved || 'NON_RENSEIGNE') !== filtrePriorite) return false
    if (query && !r.code?.toLowerCase().includes(query) && !r.designation?.toLowerCase().includes(query)) return false
    return true
  })

  const nbParStatut = s => refs.filter(r => r.statut === s).length
  const nbParClasse = c => refs.filter(r => r.classe === c).length
  const nbParRotation = f => refs.filter(r => r.fsn === f).length
  const nbParPriorite = v => refs.filter(r => (r.ved || 'NON_RENSEIGNE') === v).length

  const filtreActif = filtreStatut !== 'TOUS' || filtreClasse !== 'TOUS' || filtreRotation !== 'TOUS' || filtrePriorite !== 'TOUS' || recherche

  return (
    <div className="px-6 py-8 md:px-10 md:py-10 max-w-7xl mx-auto space-y-5">

      <PageHeader
        label="Stock"
        title="Stock"
        subtitle={chargement ? 'Chargement…' : `${refs.length} référence${refs.length > 1 ? 's' : ''} — ${refsFiltrees.length} affichée${refsFiltrees.length > 1 ? 's' : ''}`}
      />

      {/* Recherche — les filtres par colonne sont directement dans l'en-tête du tableau */}
      <div className="relative w-72">
        <svg viewBox="0 0 20 20" fill="none" className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none">
          <path d="M17.5 17.5l-4.167-4.167M14.167 8.333a5.833 5.833 0 1 1-11.667 0 5.833 5.833 0 0 1 11.667 0Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        </svg>
        <input
          type="text"
          value={recherche}
          onChange={e => setRecherche(e.target.value)}
          placeholder="Rechercher code ou désignation…"
          className="pl-9 pr-4 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 placeholder-slate-400 focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand/30 w-full"
        />
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
                  <ThFiltre
                    label="Statut"
                    value={filtreStatut}
                    onChange={setFiltreStatut}
                    options={[
                      { value: 'TOUS', label: `Tous (${refs.length})` },
                      { value: 'RUPTURE', label: `${STATUT_CFG.RUPTURE.label} (${nbParStatut('RUPTURE')})` },
                      { value: 'CRITIQUE', label: `${STATUT_CFG.CRITIQUE.label} (${nbParStatut('CRITIQUE')})` },
                      { value: 'COMMANDER', label: `${STATUT_CFG.COMMANDER.label} (${nbParStatut('COMMANDER')})` },
                      { value: 'OK', label: `${STATUT_CFG.OK.label} (${nbParStatut('OK')})` },
                    ]}
                  />
                  <th className="px-4 py-3">Code</th>
                  <th className="px-4 py-3">Désignation</th>
                  <ThFiltre
                    label="Cl."
                    align="center"
                    value={filtreClasse}
                    onChange={setFiltreClasse}
                    options={[
                      { value: 'TOUS', label: 'Toutes' },
                      { value: 'A', label: `A (${nbParClasse('A')})` },
                      { value: 'B', label: `B (${nbParClasse('B')})` },
                      { value: 'C', label: `C (${nbParClasse('C')})` },
                    ]}
                  />
                  <ThFiltre
                    label="Rotation"
                    align="center"
                    value={filtreRotation}
                    onChange={setFiltreRotation}
                    options={[
                      { value: 'TOUS', label: 'Toutes' },
                      { value: 'Fast', label: `${ROTATION_CFG.Fast.label} (${nbParRotation('Fast')})` },
                      { value: 'Slow', label: `${ROTATION_CFG.Slow.label} (${nbParRotation('Slow')})` },
                      { value: 'Non-moving', label: `${ROTATION_CFG['Non-moving'].label} (${nbParRotation('Non-moving')})` },
                    ]}
                  />
                  <ThFiltre
                    label="Priorité"
                    value={filtrePriorite}
                    onChange={setFiltrePriorite}
                    options={[
                      { value: 'TOUS', label: 'Toutes' },
                      { value: 'Vital', label: `Vital (${nbParPriorite('Vital')})` },
                      { value: 'Essentiel', label: `Essentiel (${nbParPriorite('Essentiel')})` },
                      { value: 'Désirable', label: `Désirable (${nbParPriorite('Désirable')})` },
                      { value: 'NON_RENSEIGNE', label: `Non renseigné (${nbParPriorite('NON_RENSEIGNE')})` },
                    ]}
                  />
                  <th className="px-4 py-3 text-right">Stock</th>
                  <th className="px-4 py-3 text-right">Ventes/mois</th>
                  <th className="px-4 py-3 text-right">Seuil critique</th>
                  <th className="px-4 py-3 text-right">Seuil de commande</th>
                  <th className="px-4 py-3 text-right">Qté cmd.</th>
                  <th className="px-4 py-3 text-right">Risque frs.</th>
                  <th className="px-4 py-3">Commande</th>
                </tr>
              </thead>
              <tbody>
                {refsFiltrees.length === 0 ? (
                  <tr>
                    <td colSpan={13} className="px-4 py-10 text-center text-slate-400 dark:text-slate-500 text-sm">
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
                        {/* Rotation (FSN) */}
                        <td className="px-4 py-2.5 text-center">
                          <span className={`text-xs font-medium ${ROTATION_CFG[r.fsn]?.classe || 'text-slate-500'}`}>
                            {ROTATION_CFG[r.fsn]?.label || '—'}
                          </span>
                        </td>
                        {/* Priorité (VED) éditable */}
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
                        {/* Ventes moyennes / mois (CMM) */}
                        <td className="px-4 py-2.5 text-right tabular-nums text-xs text-slate-500 dark:text-slate-400">
                          {fmtNb(r.cmm, 1)}
                        </td>
                        {/* Seuil critique (SS) */}
                        <td className="px-4 py-2.5 text-right tabular-nums text-xs text-slate-500 dark:text-slate-400">
                          {fmtNb(r.ss, 1)}
                        </td>
                        {/* Seuil de commande (PC) */}
                        <td className="px-4 py-2.5 text-right tabular-nums text-xs text-slate-500 dark:text-slate-400">
                          {fmtNb(r.pc, 1)}
                        </td>
                        {/* Qté à commander */}
                        <td className="px-4 py-2.5 text-right tabular-nums text-sm font-semibold text-slate-800 dark:text-slate-200">
                          {r.qte_a_commander > 0 ? (
                            fmtNb(r.qte_a_commander)
                          ) : estNeutralise(r) ? (
                            <span
                              className="text-xs font-normal italic text-slate-400 dark:text-slate-500"
                              title={MESSAGE_NEUTRALISE}
                            >
                              non réappro.
                            </span>
                          ) : '—'}
                        </td>
                        {/* Risque fournisseur éditable */}
                        <td className="px-4 py-2.5 text-right">
                          <RisqueCell
                            value={r.risque_fournisseur_jours}
                            saving={saving[r.id] === 'risque'}
                            onChange={jours => handleRisqueChange(r, jours)}
                          />
                        </td>
                        {/* Arbitrage manuel commande (section 6.7) */}
                        <td className="px-4 py-2.5">
                          <CommandeCell
                            ligne={r}
                            saving={saving[r.id] === 'commande'}
                            onChange={inclusionManuelle => handleCommandeChange(r, inclusionManuelle)}
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
              {filtreActif ? ` sur ${refs.length} au total` : ''}
              {' · '}Priorité modifiable uniquement pour les classes A et B
              {' · '}Cliquer sur le risque fournisseur pour modifier
            </div>
          )}
        </div>
      )}
    </div>
  )
}
