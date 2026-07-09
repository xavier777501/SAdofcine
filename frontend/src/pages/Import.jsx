import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ErrorBanner from '../components/ErrorBanner'
import ImportHistoryTable from '../components/ImportHistoryTable'
import PageHeader from '../components/PageHeader'
import { getErrorMessage } from '../services/auth'
import { marquerDirection } from '../services/pageTransition'
import { lancerCalcul } from '../services/calcul'
import {
  previewImport,
  getMapping,
  saveMapping,
  runImport,
  runImportCommande,
  autoMatchMapping,
  revalidateMapping,
  CHAMPS_LABELS,
  CHAMPS_OBLIGATOIRES,
} from '../services/imports'

export default function Import() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [typeImport, setTypeImport] = useState(null) // 'historique' | 'commande'
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [colonnes, setColonnes] = useState([])
  const [champsCibles, setChampsCibles] = useState([])
  const [mapping, setMappingState] = useState({})
  const [importResult, setImportResult] = useState(null)
  const [calculResult, setCalculResult] = useState(null)
  const [showErreurs, setShowErreurs] = useState(false)
  const [error, setError] = useState('')
  const [loadingStep, setLoadingStep] = useState(false)
  const [importing, setImporting] = useState(false)
  const [autoMapped, setAutoMapped] = useState(false)
  const [champsARevoir, setChampsARevoir] = useState([])

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

  async function handleFileSelectedCommande(selectedFile) {
    if (!selectedFile) return
    setError('')
    setFile(selectedFile)
    setImporting(true)
    try {
      const result = await runImportCommande(selectedFile)
      setImportResult(result)
      setShowErreurs(false)
      setStep(3)
    } catch (err) {
      setError(getErrorMessage(err, "Impossible d'importer le fichier Logpharma."))
      setFile(null)
    } finally {
      setImporting(false)
    }
  }

  function handleChoixType(type) {
    setTypeImport(type)
    setError('')
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
      setImporting(true)
      const result = await runImport(file)
      setImportResult(result)
      setShowErreurs(false)

      try {
        const calcul = await lancerCalcul()
        setCalculResult(calcul)
      } catch {
        setCalculResult(null)
      }

      setImporting(false)
      setStep(3)
    } catch (err) {
      setImporting(false)
      setError(getErrorMessage(err, "Impossible de lancer l'import."))
    } finally {
      setLoadingStep(false)
    }
  }

  function handleRestart() {
    setStep(1)
    setTypeImport(null)
    setFile(null)
    setColonnes([])
    setImportResult(null)
    setCalculResult(null)
    setImporting(false)
    setAutoMapped(false)
    setChampsARevoir([])
    setError('')
  }

  const erreursDetail = importResult?.erreurs_detail
    ? JSON.parse(importResult.erreurs_detail)
    : []

  return (
    <div className="px-6 py-8 md:px-10 md:py-10 max-w-3xl mx-auto space-y-8">
      <PageHeader
        label="Importer"
        title="Importer des données"
        subtitle={
          importing
            ? 'Import en cours — traitement des données…'
            : step === 1 && !typeImport
              ? 'Quel type de fichier voulez-vous importer ?'
              : step === 1 && typeImport === 'historique'
                ? 'Étape 1 sur 3 — sélection du fichier historique mensuel'
                : step === 1 && typeImport === 'commande'
                  ? 'Étape 1 sur 2 — sélection du fichier Logpharma'
                  : step === 2
                    ? 'Étape 2 sur 3 — mappage des colonnes'
                    : typeImport === 'commande'
                      ? 'Étape 2 sur 2 — résultat'
                      : 'Étape 3 sur 3 — résultat'
        }
      />

        <ErrorBanner message={error} />

        {importing && (
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-10 flex flex-col items-center gap-6 text-center">
            <div className="relative w-16 h-16">
              <svg className="w-16 h-16 -rotate-90 animate-[spin_2s_linear_infinite]" viewBox="0 0 64 64">
                <circle
                  cx="32" cy="32" r="26"
                  fill="none" stroke="currentColor" strokeWidth="6" className="text-slate-200 dark:text-slate-700"
                />
                <circle
                  cx="32" cy="32" r="26"
                  fill="none" stroke="currentColor" strokeWidth="6"
                  strokeDasharray="163.36"
                  strokeDashoffset="40.84"
                  strokeLinecap="round"
                  className="text-brand"
                />
              </svg>
            </div>
            <div>
              <p className="text-base font-semibold text-slate-900 dark:text-slate-100">Import en cours…</p>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                {file?.name && <span className="font-medium text-slate-700 dark:text-slate-300">{file.name}</span>}
              </p>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-3 max-w-xs">
                Le traitement des lignes peut prendre quelques minutes pour un fichier volumineux.
                Ne fermez pas cette fenêtre.
              </p>
            </div>
            <div className="w-full max-w-xs">
              <div className="h-1.5 w-full bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-brand rounded-full"
                  style={{
                    animation: 'progress-fill 120s cubic-bezier(0.1, 0.4, 0.5, 1) forwards',
                  }}
                />
              </div>
            </div>
            <style>{`
              @keyframes progress-fill {
                0%   { width: 0%; }
                20%  { width: 30%; }
                50%  { width: 55%; }
                80%  { width: 80%; }
                100% { width: 92%; }
              }
            `}</style>
          </div>
        )}

        {!importing && step === 1 && !typeImport && (
          <div className="grid gap-4 sm:grid-cols-2">
            <button
              type="button"
              onClick={() => handleChoixType('historique')}
              className="tg-tap text-left rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 hover:border-brand hover:shadow-brand/20 hover:shadow-md transition-all"
            >
              <div className="text-2xl mb-3">📋</div>
              <p className="font-semibold text-slate-900 dark:text-slate-100 mb-1">Mettre à jour l'historique mensuel</p>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Importez le fichier "Données mensuelles" avec 12 mois de ventes. Permet le recalcul complet (CMM, stock de sécurité, ABC…).
              </p>
            </button>

            <button
              type="button"
              onClick={() => handleChoixType('commande')}
              className="tg-tap text-left rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 hover:border-brand hover:shadow-brand/20 hover:shadow-md transition-all"
            >
              <div className="text-2xl mb-3">🛒</div>
              <p className="font-semibold text-slate-900 dark:text-slate-100 mb-1">Préparer ma commande</p>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Importez l'export Logpharma "Listing de Produit à Commander" pour mettre à jour le stock actuel et voir quoi commander.
              </p>
            </button>
          </div>
        )}

        {!importing && step === 1 && typeImport === 'historique' && (
          <div
            onDragOver={(e) => {
              e.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            className={`rounded-2xl border-2 border-dashed p-12 text-center transition ${
              dragging
                ? 'border-brand bg-brand-light dark:bg-brand/10'
                : 'border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800'
            }`}
          >
            <p className="text-slate-600 dark:text-slate-300 mb-1">
              Glissez-déposez votre fichier ici, ou choisissez-le manuellement.
            </p>
            <p className="text-xs text-slate-400 dark:text-slate-500 mb-4">Formats acceptés : .xlsx, .xls, .csv</p>
            <label className="tg-tap inline-block rounded-lg bg-brand-gradient px-4 py-2.5 font-semibold text-white shadow-sm cursor-pointer transition-all hover:shadow-brand hover:-translate-y-0.5">
              {loadingStep ? 'Lecture en cours…' : 'Choisir le fichier historique'}
              <input
                type="file"
                accept=".xlsx,.xls,.csv"
                className="hidden"
                disabled={loadingStep}
                onChange={(e) => handleFileSelected(e.target.files?.[0])}
              />
            </label>
            <button onClick={handleRestart} className="block mx-auto mt-4 text-sm text-slate-400 hover:underline">
              ← Retour
            </button>
          </div>
        )}

        {!importing && step === 1 && typeImport === 'commande' && (
          <div className="rounded-2xl border-2 border-dashed border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 p-12 text-center">
            <p className="text-slate-600 dark:text-slate-300 mb-1">
              Sélectionnez l'export Logpharma "Listing de Produit à Commander".
            </p>
            <p className="text-xs text-slate-400 dark:text-slate-500 mb-4">Format .xlsx uniquement — pas de mappage nécessaire</p>
            <label className="tg-tap inline-block rounded-lg bg-brand-gradient px-4 py-2.5 font-semibold text-white shadow-sm cursor-pointer transition-all hover:shadow-brand hover:-translate-y-0.5">
              {importing ? 'Import en cours…' : 'Choisir le fichier Logpharma'}
              <input
                type="file"
                accept=".xlsx,.xls"
                className="hidden"
                disabled={importing}
                onChange={(e) => handleFileSelectedCommande(e.target.files?.[0])}
              />
            </label>
            <button onClick={handleRestart} className="block mx-auto mt-4 text-sm text-slate-400 hover:underline">
              ← Retour
            </button>
          </div>
        )}

        {!importing && step === 2 && (
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-6 space-y-5">
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Fichier : <span className="font-medium text-slate-900 dark:text-slate-100">{file?.name}</span>
            </p>
            {autoMapped && (
              <p className="rounded-lg bg-info-light dark:bg-info/10 border border-info/30 text-info text-sm px-4 py-3">
                Mappage détecté automatiquement à partir des noms de colonnes — vérifiez et corrigez si besoin.
              </p>
            )}
            {champsARevoir.length > 0 && (
              <p className="rounded-lg bg-orange-50 dark:bg-orange-500/10 border border-orange-300 dark:border-orange-500/40 text-orange-700 dark:text-orange-400 text-sm px-4 py-3">
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
                    <label className="w-64 shrink-0 text-sm font-medium text-slate-700 dark:text-slate-300">
                      {CHAMPS_LABELS[champ] || champ}
                      {obligatoire && <span className="text-danger"> *</span>}
                    </label>
                    <select
                      value={mapping[champ] || ''}
                      onChange={(e) => updateMapping(champ, e.target.value)}
                      className={`flex-1 rounded-lg border px-3 py-2 text-slate-900 dark:text-slate-100 shadow-sm focus:outline-none focus:ring-2 focus:ring-brand ${
                        aRevoir
                          ? 'border-orange-400 dark:border-orange-500 bg-orange-50 dark:bg-orange-500/10'
                          : 'border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900'
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
              <button onClick={handleRestart} className="tg-tap text-sm text-slate-500 dark:text-slate-400 hover:underline">
                Annuler
              </button>
              <button
                onClick={handleSaveMappingAndImport}
                disabled={loadingStep || mappingIncomplete()}
                className="tg-tap rounded-lg bg-brand-gradient px-4 py-2.5 font-semibold text-white shadow-sm transition-all hover:shadow-brand hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0 disabled:hover:shadow-sm"
              >
                {loadingStep ? 'Import en cours…' : "Sauvegarder le mappage et lancer l'import"}
              </button>
            </div>
          </div>
        )}

        {!importing && step === 3 && importResult && (
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-6 space-y-4">
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Fichier : <span className="font-medium text-slate-900 dark:text-slate-100">{importResult.nom_fichier}</span>
            </p>
            <div className="flex gap-4">
              <div className="flex-1 rounded-lg bg-brand-light dark:bg-brand/10 border border-brand/30 px-4 py-3 text-center">
                <p className="text-2xl font-semibold text-brand-dark dark:text-brand">{importResult.nb_lignes_ok ?? 0}</p>
                <p className="text-xs text-brand-dark dark:text-brand">lignes importées</p>
              </div>
              <div className="flex-1 rounded-lg bg-orange-50 dark:bg-orange-500/10 border border-orange-300 dark:border-orange-500/40 px-4 py-3 text-center">
                <p className="text-2xl font-semibold text-orange-600 dark:text-orange-400">{importResult.nb_lignes_erreur ?? 0}</p>
                <p className="text-xs text-orange-600 dark:text-orange-400">lignes en erreur</p>
              </div>
            </div>

            {calculResult && (
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {calculResult.nb_references} références recalculées — {calculResult.nb_a_commander} à commander
              </p>
            )}

            {typeImport === 'commande' && (
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Stocks mis à jour et recommandations recalculées.{' '}
                <button
                  type="button"
                  onClick={() => { marquerDirection('/import', '/quoi-commander'); navigate('/quoi-commander', { viewTransition: true }) }}
                  className="font-medium text-brand hover:underline"
                >
                  Voir quoi commander →
                </button>
              </p>
            )}

            {importResult.nb_lignes_erreur > 0 && (
              <div>
                <button
                  onClick={() => setShowErreurs((prev) => !prev)}
                  className="tg-tap text-sm font-medium text-brand hover:underline"
                >
                  {showErreurs ? 'Masquer les erreurs' : 'Voir les erreurs'}
                </button>
                {showErreurs && (
                  <ul className="mt-3 space-y-1 max-h-64 overflow-y-auto text-sm">
                    {erreursDetail.map((e, i) => (
                      <li key={i} className="rounded bg-slate-50 dark:bg-slate-900/60 px-3 py-2 text-slate-600 dark:text-slate-300">
                        Ligne {e.ligne} — {e.raison}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            <button
              onClick={() => {
                marquerDirection('/import', '/dashboard')
                navigate('/dashboard', { viewTransition: true })
              }}
              className="tg-tap w-full rounded-lg bg-brand-gradient px-4 py-2.5 font-semibold text-white shadow-sm transition-all hover:shadow-brand hover:-translate-y-0.5"
            >
              Voir le tableau de bord
            </button>

            <button
              onClick={handleRestart}
              className="tg-tap w-full rounded-lg border border-brand px-4 py-2.5 font-semibold text-brand transition hover:bg-brand-light dark:hover:bg-brand/10"
            >
              Importer un autre fichier
            </button>
          </div>
        )}

        <ImportHistoryTable key={importResult?.id || 'aucun'} />
    </div>
  )
}
