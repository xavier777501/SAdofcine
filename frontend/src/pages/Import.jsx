import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ErrorBanner from '../components/ErrorBanner'
import Logo from '../components/Logo'
import { getErrorMessage } from '../services/auth'
import {
  previewImport,
  getMapping,
  saveMapping,
  runImport,
  getImportHistory,
  autoMatchMapping,
  revalidateMapping,
  CHAMPS_LABELS,
  CHAMPS_OBLIGATOIRES,
} from '../services/imports'

const STATUT_STYLES = {
  succes: 'bg-brand-light text-brand-dark border-brand/30',
  en_cours: 'bg-info-light text-info border-info/30',
  erreur: 'bg-danger-light text-danger border-danger/30',
}

function formatDate(iso) {
  return new Date(iso).toLocaleString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function Import() {
  const navigate = useNavigate()

  const [step, setStep] = useState(1)
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [colonnes, setColonnes] = useState([])
  const [champsCibles, setChampsCibles] = useState([])
  const [mapping, setMappingState] = useState({})
  const [importResult, setImportResult] = useState(null)
  const [showErreurs, setShowErreurs] = useState(false)
  const [history, setHistory] = useState([])
  const [error, setError] = useState('')
  const [loadingStep, setLoadingStep] = useState(false)
  const [autoMapped, setAutoMapped] = useState(false)
  const [champsARevoir, setChampsARevoir] = useState([])

  useEffect(() => {
    loadHistory()
  }, [])

  async function loadHistory() {
    try {
      const data = await getImportHistory()
      setHistory(data)
    } catch {
      // historique optionnel, on n'affiche pas d'erreur bloquante
    }
  }

  async function handleFileSelected(selectedFile) {
    if (!selectedFile) return
    setError('')
    setFile(selectedFile)
    setLoadingStep(true)
    try {
      const preview = await previewImport(selectedFile)
      setColonnes(preview.colonnes)

      const { champs_cibles, mapping: savedMapping } = await getMapping()
      setChampsCibles(champs_cibles)

      if (Object.keys(savedMapping).length > 0) {
        const { valide, aRevoir } = revalidateMapping(savedMapping, preview.colonnes)

        if (aRevoir.length > 0) {
          const detectePourManquants = autoMatchMapping(preview.colonnes, aRevoir)
          setMappingState({ ...valide, ...detectePourManquants })
          setChampsARevoir(aRevoir)
        } else {
          setMappingState(valide)
          setChampsARevoir([])
        }
        setAutoMapped(false)
      } else {
        const detecte = autoMatchMapping(preview.colonnes, champs_cibles)
        setMappingState(detecte)
        setAutoMapped(Object.keys(detecte).length > 0)
        setChampsARevoir([])
      }

      setStep(2)
    } catch (err) {
      setError(getErrorMessage(err, "Impossible de lire ce fichier."))
      setFile(null)
    } finally {
      setLoadingStep(false)
    }
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragging(false)
    handleFileSelected(e.dataTransfer.files?.[0])
  }

  function updateMapping(champ, colonne) {
    setMappingState((prev) => ({ ...prev, [champ]: colonne }))
  }

  function mappingIncomplete() {
    return CHAMPS_OBLIGATOIRES.some((champ) => !mapping[champ])
  }

  async function handleSaveMappingAndImport() {
    setError('')
    setLoadingStep(true)
    try {
      await saveMapping(mapping)
      const result = await runImport(file)
      setImportResult(result)
      setShowErreurs(false)
      setStep(3)
      loadHistory()
    } catch (err) {
      setError(getErrorMessage(err, "Impossible de lancer l'import."))
    } finally {
      setLoadingStep(false)
    }
  }

  function handleRestart() {
    setStep(1)
    setFile(null)
    setColonnes([])
    setImportResult(null)
    setAutoMapped(false)
    setChampsARevoir([])
    setError('')
  }

  const erreursDetail = importResult?.erreurs_detail
    ? JSON.parse(importResult.erreurs_detail)
    : []

  return (
    <div className="min-h-screen bg-surface">
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Logo className="h-9 w-9 rounded-lg" />
          <p className="brand-name text-lg leading-none text-slate-900">StockAid</p>
        </div>
        <button
          onClick={() => navigate('/dashboard')}
          className="rounded-lg border border-slate-300 text-slate-600 px-4 py-2 text-sm font-medium hover:bg-slate-50"
        >
          ← Retour au tableau de bord
        </button>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Importer des données</h1>
          <p className="mt-1 text-slate-500 text-sm">
            Étape {step} sur 3 — {step === 1 ? 'sélection du fichier' : step === 2 ? 'mappage des colonnes' : 'résultat'}
          </p>
        </div>

        <ErrorBanner message={error} />

        {step === 1 && (
          <div
            onDragOver={(e) => {
              e.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            className={`rounded-2xl border-2 border-dashed p-12 text-center transition ${
              dragging ? 'border-brand bg-brand-light' : 'border-slate-300 bg-white'
            }`}
          >
            <p className="text-slate-600 mb-4">
              Glissez-déposez votre fichier ici, ou choisissez-le manuellement.
            </p>
            <p className="text-xs text-slate-400 mb-4">Formats acceptés : .xlsx, .xls, .csv</p>
            <label className="inline-block rounded-lg bg-brand px-4 py-2.5 font-semibold text-white cursor-pointer transition hover:bg-brand-dark">
              {loadingStep ? 'Lecture en cours…' : 'Choisir un fichier'}
              <input
                type="file"
                accept=".xlsx,.xls,.csv"
                className="hidden"
                disabled={loadingStep}
                onChange={(e) => handleFileSelected(e.target.files?.[0])}
              />
            </label>
          </div>
        )}

        {step === 2 && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-5">
            <p className="text-sm text-slate-600">
              Fichier : <span className="font-medium text-slate-900">{file?.name}</span>
            </p>
            {autoMapped && (
              <p className="rounded-lg bg-info-light border border-info/30 text-info text-sm px-4 py-3">
                Mappage détecté automatiquement à partir des noms de colonnes — vérifiez et corrigez si besoin.
              </p>
            )}
            {champsARevoir.length > 0 && (
              <p className="rounded-lg bg-orange-50 border border-orange-300 text-orange-700 text-sm px-4 py-3">
                Les colonnes de ce fichier ont changé depuis le dernier import (ex : les mois ont avancé).
                Vérifiez les champs surlignés ci-dessous — les autres ont été conservés tels quels.
              </p>
            )}
            <div className="space-y-3">
              {champsCibles.map((champ) => {
                const obligatoire = CHAMPS_OBLIGATOIRES.includes(champ)
                const aRevoir = champsARevoir.includes(champ)
                return (
                  <div key={champ} className="flex items-center gap-3">
                    <label className="w-64 shrink-0 text-sm font-medium text-slate-700">
                      {CHAMPS_LABELS[champ] || champ}
                      {obligatoire && <span className="text-danger"> *</span>}
                    </label>
                    <select
                      value={mapping[champ] || ''}
                      onChange={(e) => updateMapping(champ, e.target.value)}
                      className={`flex-1 rounded-lg border px-3 py-2 text-slate-900 shadow-sm focus:outline-none focus:ring-2 focus:ring-brand ${
                        aRevoir ? 'border-orange-400 bg-orange-50' : 'border-slate-300'
                      }`}
                    >
                      <option value="">— Non mappé —</option>
                      {colonnes.map((col) => (
                        <option key={col} value={col}>
                          {col}
                        </option>
                      ))}
                    </select>
                  </div>
                )
              })}
            </div>
            <div className="flex items-center justify-between pt-2">
              <button onClick={handleRestart} className="text-sm text-slate-500 hover:underline">
                Annuler
              </button>
              <button
                onClick={handleSaveMappingAndImport}
                disabled={loadingStep || mappingIncomplete()}
                className="rounded-lg bg-brand px-4 py-2.5 font-semibold text-white transition hover:bg-brand-dark disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loadingStep ? 'Import en cours…' : "Sauvegarder le mappage et lancer l'import"}
              </button>
            </div>
          </div>
        )}

        {step === 3 && importResult && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-4">
            <p className="text-sm text-slate-600">
              Fichier : <span className="font-medium text-slate-900">{importResult.nom_fichier}</span>
            </p>
            <div className="flex gap-4">
              <div className="flex-1 rounded-lg bg-brand-light border border-brand/30 px-4 py-3 text-center">
                <p className="text-2xl font-semibold text-brand-dark">{importResult.nb_lignes_ok ?? 0}</p>
                <p className="text-xs text-brand-dark">lignes importées</p>
              </div>
              <div className="flex-1 rounded-lg bg-orange-50 border border-orange-300 px-4 py-3 text-center">
                <p className="text-2xl font-semibold text-orange-600">{importResult.nb_lignes_erreur ?? 0}</p>
                <p className="text-xs text-orange-600">lignes en erreur</p>
              </div>
            </div>

            {importResult.nb_lignes_erreur > 0 && (
              <div>
                <button
                  onClick={() => setShowErreurs((prev) => !prev)}
                  className="text-sm font-medium text-brand hover:underline"
                >
                  {showErreurs ? 'Masquer les erreurs' : 'Voir les erreurs'}
                </button>
                {showErreurs && (
                  <ul className="mt-3 space-y-1 max-h-64 overflow-y-auto text-sm">
                    {erreursDetail.map((e, i) => (
                      <li key={i} className="rounded bg-slate-50 px-3 py-2 text-slate-600">
                        Ligne {e.ligne} — {e.raison}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            <button
              onClick={handleRestart}
              className="w-full rounded-lg border border-brand px-4 py-2.5 font-semibold text-brand transition hover:bg-brand-light"
            >
              Importer un autre fichier
            </button>
          </div>
        )}

        <section>
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Historique des imports</h2>
          {history.length === 0 ? (
            <p className="text-sm text-slate-400">Aucun import pour le moment.</p>
          ) : (
            <div className="overflow-x-auto bg-white rounded-xl border border-slate-200">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-slate-500">
                    <th className="px-4 py-2 font-medium">Date</th>
                    <th className="px-4 py-2 font-medium">Fichier</th>
                    <th className="px-4 py-2 font-medium">Statut</th>
                    <th className="px-4 py-2 font-medium">Lignes OK</th>
                    <th className="px-4 py-2 font-medium">Lignes erreur</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((h) => (
                    <tr key={h.id} className="border-b border-slate-100 last:border-0">
                      <td className="px-4 py-2 text-slate-600">{formatDate(h.created_at)}</td>
                      <td className="px-4 py-2 text-slate-900">{h.nom_fichier}</td>
                      <td className="px-4 py-2">
                        <span
                          className={`inline-block rounded-full border px-2 py-0.5 text-xs font-medium ${
                            STATUT_STYLES[h.statut] || 'bg-slate-100 text-slate-600 border-slate-300'
                          }`}
                        >
                          {h.statut}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-slate-600">{h.nb_lignes_ok ?? '—'}</td>
                      <td className="px-4 py-2 text-slate-600">{h.nb_lignes_erreur ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
