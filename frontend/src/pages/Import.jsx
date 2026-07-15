import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ErrorBanner from '../components/ErrorBanner'
import ImportHistoryTable from '../components/ImportHistoryTable'
import PageHeader from '../components/PageHeader'
import { getErrorMessage } from '../services/auth'
import { marquerDirection } from '../services/pageTransition'
import {
  runImportCommande,
  runImportHistoriqueLogpharma,
  runImportHistoriqueAnnuel,
  getEtatImport,
  previewImport,
  getMapping,
  saveMapping,
  runImport,
  autoMatchMapping,
  revalidateMapping,
  CHAMPS_LABELS,
  CHAMPS_OBLIGATOIRES,
} from '../services/imports'
import { lancerCalcul } from '../services/calcul'

const NOMS_MOIS_AFFICHAGE = [
  'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
]

/**
 * Libellé du mois "k mois avant aujourd'hui" (k=1 -> le plus récent complet,
 * k=12 -> le plus ancien de la fenêtre glissante). Purement indicatif côté
 * écran : le backend ne demande pas de mois précis, il ajoute toujours le
 * fichier reçu comme le plus récent — mais afficher le vrai nom du mois rend
 * le parcours d'initialisation clair et guidé plutôt qu'un bouton générique.
 */
function libelleMoisPasse(k, aujourdHui = new Date()) {
  const moisActuel = aujourdHui.getMonth()
  const anneeActuelle = aujourdHui.getFullYear()
  const decalage = moisActuel - k
  const moisIndexJS = ((decalage % 12) + 12) % 12
  const annee = anneeActuelle + Math.floor(decalage / 12)
  return `${NOMS_MOIS_AFFICHAGE[moisIndexJS]} ${annee}`
}

// Les 12 mois de la fenêtre glissante, du plus ancien au plus récent (M-12 → M-1).
const LISTE_12_MOIS = Array.from({ length: 12 }, (_, i) => libelleMoisPasse(12 - i))

export default function Import() {
  const navigate = useNavigate()
  const [typeImport, setTypeImport] = useState(null) // 'historique' | 'commande'
  const [moisStatus, setMoisStatus] = useState({}) // { [index]: { statut, result?, error? } }
  const [historiqueDejaComplet, setHistoriqueDejaComplet] = useState(false)
  const [maintenanceStatut, setMaintenanceStatut] = useState(null) // { statut, result?, error? }
  const [annuelStatus, setAnnuelStatus] = useState(null) // { statut, result?, error? }
  const [file, setFile] = useState(null)
  const [importResult, setImportResult] = useState(null)
  const [showErreurs, setShowErreurs] = useState(false)
  const [error, setError] = useState('')
  const [importing, setImporting] = useState(false)
  const [step, setStep] = useState(1)

  // Sous-flux "j'ai un fichier avec les 12 mois déjà en colonnes" (mappage
  // manuel, section 9 du cahier des charges — import tolérant) : une
  // alternative au format fixe, pour une pharmacie dont l'export diffère.
  const [mappageStep, setMappageStep] = useState(1)
  const [mappageFile, setMappageFile] = useState(null)
  const [mappageColonnes, setMappageColonnes] = useState([])
  const [mappageChampsCibles, setMappageChampsCibles] = useState([])
  const [mappageMapping, setMappageMapping] = useState({})
  const [mappageAutoMapped, setMappageAutoMapped] = useState(false)
  const [mappageChampsARevoir, setMappageChampsARevoir] = useState([])
  const [mappageResult, setMappageResult] = useState(null)
  const [mappageCalculResult, setMappageCalculResult] = useState(null)
  const [mappageLoadingStep, setMappageLoadingStep] = useState(false)
  const [mappageImporting, setMappageImporting] = useState(false)
  const [mappageError, setMappageError] = useState('')
  const [mappageShowErreurs, setMappageShowErreurs] = useState(false)

  // Charge en arrière-plan l'état réel de l'historique (combien de mois sont
  // déjà enregistrés côté serveur), pour que l'écran affiché après le choix
  // du pharmacien retrouve où il en est — sans jamais choisir à sa place.
  function chargerEtatHistorique() {
    getEtatImport()
      .then(({ nb_mois_historique }) => {
        const dejaRemplis = Math.min(nb_mois_historique || 0, 12)
        if (dejaRemplis >= 12) {
          // Déjà entièrement calibré : la liste des 12 mois n'a plus de sens
          // (impossible de savoir quel mois précis manque une fois la fenêtre
          // glissante bouclée au moins une fois) — mode entretien mensuel.
          setHistoriqueDejaComplet(true)
        } else if (dejaRemplis > 0) {
          const initial = {}
          for (let i = 0; i < dejaRemplis; i++) {
            initial[i] = { statut: 'ok', dejaFait: true }
          }
          setMoisStatus(initial)
        }
      })
      .catch(() => {})
  }

  useEffect(() => {
    chargerEtatHistorique()
  }, [])

  function handleChoixType(type) {
    setTypeImport(type)
    setError('')
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

  async function handleFileSelectedHistorique(index, selectedFile) {
    if (!selectedFile) return
    setMoisStatus((prev) => ({ ...prev, [index]: { statut: 'en_cours' } }))
    try {
      const result = await runImportHistoriqueLogpharma(selectedFile)
      setMoisStatus((prev) => ({ ...prev, [index]: { statut: 'ok', result } }))
    } catch (err) {
      setMoisStatus((prev) => ({
        ...prev,
        [index]: { statut: 'erreur', error: getErrorMessage(err, "Impossible d'importer ce fichier.") },
      }))
    }
  }

  async function handleFileSelectedMaintenance(selectedFile) {
    if (!selectedFile) return
    setMaintenanceStatut({ statut: 'en_cours' })
    try {
      const result = await runImportHistoriqueLogpharma(selectedFile)
      setMaintenanceStatut({ statut: 'ok', result })
    } catch (err) {
      setMaintenanceStatut({ statut: 'erreur', error: getErrorMessage(err, "Impossible d'importer ce fichier.") })
    }
  }

  async function handleFileSelectedAnnuel(selectedFile) {
    if (!selectedFile) return
    setAnnuelStatus({ statut: 'en_cours' })
    try {
      const result = await runImportHistoriqueAnnuel(selectedFile)
      setAnnuelStatus({ statut: 'ok', result })
    } catch (err) {
      setAnnuelStatus({ statut: 'erreur', error: getErrorMessage(err, "Impossible d'importer ce fichier.") })
    }
  }

  async function handleMappageFileSelected(selectedFile) {
    if (!selectedFile) return
    setMappageError('')
    setMappageFile(selectedFile)
    setMappageLoadingStep(true)
    try {
      const preview = await previewImport(selectedFile)
      setMappageColonnes(preview.colonnes)

      const { champs_cibles, mapping: savedMapping } = await getMapping()
      setMappageChampsCibles(champs_cibles)

      if (Object.keys(savedMapping).length > 0) {
        const { valide, aRevoir } = revalidateMapping(savedMapping, preview.colonnes)
        if (aRevoir.length > 0) {
          const detectePourManquants = autoMatchMapping(preview.colonnes, aRevoir)
          setMappageMapping({ ...valide, ...detectePourManquants })
          setMappageChampsARevoir(aRevoir)
        } else {
          setMappageMapping(valide)
          setMappageChampsARevoir([])
        }
        setMappageAutoMapped(false)
      } else {
        const detecte = autoMatchMapping(preview.colonnes, champs_cibles)
        setMappageMapping(detecte)
        setMappageAutoMapped(Object.keys(detecte).length > 0)
        setMappageChampsARevoir([])
      }

      setMappageStep(2)
    } catch (err) {
      setMappageError(getErrorMessage(err, "Impossible de lire ce fichier."))
      setMappageFile(null)
    } finally {
      setMappageLoadingStep(false)
    }
  }

  function updateMappageChamp(champ, colonne) {
    setMappageMapping((prev) => ({ ...prev, [champ]: colonne }))
  }

  function mappageIncomplet() {
    return CHAMPS_OBLIGATOIRES.some((champ) => !mappageMapping[champ])
  }

  async function handleMappageSaveAndImport() {
    setMappageError('')
    setMappageLoadingStep(true)
    try {
      await saveMapping(mappageMapping)
      setMappageImporting(true)
      const result = await runImport(mappageFile)
      setMappageResult(result)
      setMappageShowErreurs(false)

      try {
        const calcul = await lancerCalcul()
        setMappageCalculResult(calcul)
      } catch {
        setMappageCalculResult(null)
      }

      setMappageImporting(false)
      setMappageStep(3)
    } catch (err) {
      setMappageImporting(false)
      setMappageError(getErrorMessage(err, "Impossible de lancer l'import."))
    } finally {
      setMappageLoadingStep(false)
    }
  }

  function handleMappageRestart() {
    setMappageStep(1)
    setMappageFile(null)
    setMappageColonnes([])
    setMappageResult(null)
    setMappageCalculResult(null)
    setMappageImporting(false)
    setMappageAutoMapped(false)
    setMappageChampsARevoir([])
    setMappageError('')
  }

  function handleRestart() {
    setStep(1)
    setTypeImport(null)
    setMoisStatus({})
    setHistoriqueDejaComplet(false)
    setMaintenanceStatut(null)
    setAnnuelStatus(null)
    setFile(null)
    setImportResult(null)
    setImporting(false)
    setError('')
    handleMappageRestart()
    chargerEtatHistorique()
  }

  const erreursDetail = importResult?.erreurs_detail
    ? JSON.parse(importResult.erreurs_detail)
    : []

  const nbMoisFaits = Object.values(moisStatus).filter((m) => m.statut === 'ok').length
  const indexProchain = LISTE_12_MOIS.findIndex((_, i) => moisStatus[i]?.statut !== 'ok')

  return (
    <div className="px-6 py-8 md:px-10 md:py-10 max-w-3xl mx-auto space-y-8">
      <PageHeader
        label="Importer"
        title="Importer des données"
        subtitle={
          importing
            ? 'Import en cours — traitement des données…'
            : !typeImport
              ? 'Quel type de fichier voulez-vous importer ?'
              : typeImport === 'historique'
                ? 'Calibrer le moteur de calcul — pas pour passer une commande'
                : step === 1
                  ? 'Sélection du fichier Logpharma'
                  : 'Résultat'
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

        {!importing && !typeImport && (
          <div className="grid gap-4 sm:grid-cols-2">
            <button
              type="button"
              onClick={() => handleChoixType('historique')}
              className="tg-tap text-left rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 hover:border-brand hover:shadow-brand/20 hover:shadow-md transition-all"
            >
              <div className="text-2xl mb-3">📋</div>
              <p className="font-semibold text-slate-900 dark:text-slate-100 mb-1">Mettre à jour l'historique mensuel</p>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Calibre le moteur de calcul (ventes moyennes, seuils, priorités) — ne sert pas à passer une commande.
                Importez vos exports Logpharma mois par mois (jusqu'à 12).
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

        {!importing && typeImport === 'historique' && (
          <div className="space-y-4">
            <div className="rounded-xl bg-info-light dark:bg-info/10 border border-info/30 px-5 py-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-info">Ceci ne sert pas à passer une commande.</p>
                <p className="mt-1 text-xs text-info/90">
                  Cette page calibre uniquement la précision du moteur de calcul (ventes moyennes, seuils, priorités).
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleChoixType('commande')}
                className="tg-tap shrink-0 inline-flex items-center gap-1.5 rounded-lg bg-white dark:bg-slate-800 border border-info text-info px-4 py-2 text-sm font-semibold shadow-sm transition-all hover:bg-info hover:text-white hover:shadow-md"
              >
                Préparer ma commande
                <svg viewBox="0 0 16 16" className="w-3.5 h-3.5" fill="none" aria-hidden="true">
                  <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </div>

            {historiqueDejaComplet && nbMoisFaits === 0 ? (
              <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-brand/40 p-8 text-center space-y-3">
                <p className="text-sm font-semibold text-brand-dark dark:text-brand">
                  Historique complet — 12/12 mois déjà enregistrés
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                  Revenez ici une fois par mois pour ajouter le mois qui vient de se terminer — le plus ancien sortira
                  automatiquement de l'historique.
                </p>
                <label className="tg-tap inline-block rounded-lg bg-brand-gradient px-4 py-2.5 font-semibold text-white shadow-sm cursor-pointer transition-all hover:shadow-brand hover:-translate-y-0.5">
                  {maintenanceStatut?.statut === 'en_cours'
                    ? 'Import en cours…'
                    : `Choisir le fichier de ${LISTE_12_MOIS[11]}`}
                  <input
                    type="file"
                    accept=".xlsx,.xls"
                    className="hidden"
                    disabled={maintenanceStatut?.statut === 'en_cours'}
                    onChange={(e) => handleFileSelectedMaintenance(e.target.files?.[0])}
                  />
                </label>
                {maintenanceStatut?.statut === 'ok' && (
                  <p className="text-xs text-brand-dark dark:text-brand">
                    {maintenanceStatut.result.nb_lignes_ok} références mises à jour
                    {maintenanceStatut.result.nb_lignes_erreur > 0 && ` — ${maintenanceStatut.result.nb_lignes_erreur} en erreur`}
                  </p>
                )}
                {maintenanceStatut?.statut === 'erreur' && (
                  <p className="text-xs text-danger">{maintenanceStatut.error}</p>
                )}
              </div>
            ) : (
              <>
                <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
                  <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100 dark:border-slate-700">
                    <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                      Historique à compléter, mois par mois
                    </p>
                    <p className="text-xs text-slate-400 dark:text-slate-500">{nbMoisFaits}/12 importés</p>
                  </div>

                  <ul className="divide-y divide-slate-100 dark:divide-slate-700">
                    {LISTE_12_MOIS.map((label, index) => {
                      const statut = moisStatus[index]
                      const estProchain = index === indexProchain
                      return (
                        <li
                          key={label}
                          className={`flex items-center justify-between gap-3 px-5 py-3 ${
                            estProchain ? 'bg-brand-light/50 dark:bg-brand/10' : ''
                          }`}
                        >
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{label}</p>
                            {statut?.statut === 'ok' && statut.dejaFait && (
                              <p className="text-xs text-slate-400 dark:text-slate-500">Déjà enregistré</p>
                            )}
                            {statut?.statut === 'ok' && !statut.dejaFait && (
                              <p className="text-xs text-brand-dark dark:text-brand">
                                {statut.result.nb_lignes_ok} références mises à jour
                                {statut.result.nb_lignes_erreur > 0 && ` — ${statut.result.nb_lignes_erreur} en erreur`}
                              </p>
                            )}
                            {statut?.statut === 'erreur' && (
                              <p className="text-xs text-danger">{statut.error}</p>
                            )}
                          </div>

                          <div className="shrink-0 flex items-center gap-2">
                            {statut?.statut === 'ok' && <span className="text-brand-dark dark:text-brand text-lg">✓</span>}
                            <label className={`tg-tap inline-block rounded-lg px-3 py-1.5 text-xs font-semibold cursor-pointer transition ${
                              statut?.statut === 'ok'
                                ? 'border border-slate-300 dark:border-slate-600 text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700'
                                : 'bg-brand-gradient text-white shadow-sm hover:shadow-brand'
                            }`}>
                              {statut?.statut === 'en_cours'
                                ? 'Import…'
                                : statut?.statut === 'ok'
                                  ? 'Remplacer'
                                  : 'Choisir le fichier'}
                              <input
                                type="file"
                                accept=".xlsx,.xls"
                                className="hidden"
                                disabled={statut?.statut === 'en_cours'}
                                onChange={(e) => handleFileSelectedHistorique(index, e.target.files?.[0])}
                              />
                            </label>
                          </div>
                        </li>
                      )
                    })}
                  </ul>
                </div>

                {nbMoisFaits >= 12 && (
                  <p className="text-sm text-brand-dark dark:text-brand text-center">
                    Historique complet — les seuils et recommandations sont fiables. Pour la suite, revenez ici une
                    fois par mois pour ajouter le mois qui vient de se terminer (le plus ancien sortira automatiquement).
                  </p>
                )}
              </>
            )}

            <details className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/40 p-4">
              <summary className="text-sm font-semibold text-slate-600 dark:text-slate-300 cursor-pointer">
                Raccourci temporaire : importer un seul fichier compilé (moins précis, à éviter si possible)
              </summary>
              <div className="mt-3 space-y-3">
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Utile seulement pour avoir une estimation immédiate en attendant de compléter les 12 mois ci-dessus.
                  Ce fichier ne donne qu'une consommation moyenne approximative — <strong>jamais</strong> de stock de
                  sécurité ni de statut fiable (rupture/critique/à commander), puisqu'il ne contient pas le détail mois
                  par mois. Ne remplace pas l'import mensuel.
                </p>

                {annuelStatus?.statut === 'ok' && (
                  <p className="text-xs text-brand-dark dark:text-brand">
                    {annuelStatus.result.nb_lignes_ok} références initialisées (estimation seulement)
                    {annuelStatus.result.nb_lignes_erreur > 0 && ` — ${annuelStatus.result.nb_lignes_erreur} en erreur`}
                  </p>
                )}
                {annuelStatus?.statut === 'erreur' && (
                  <p className="text-xs text-danger">{annuelStatus.error}</p>
                )}

                <label className="tg-tap inline-block rounded-lg border border-slate-400 dark:border-slate-500 px-3 py-1.5 text-sm font-medium text-slate-600 dark:text-slate-300 cursor-pointer transition hover:bg-white dark:hover:bg-slate-800">
                  {annuelStatus?.statut === 'en_cours' ? 'Import en cours…' : 'Choisir le fichier compilé'}
                  <input
                    type="file"
                    accept=".xlsx,.xls"
                    className="hidden"
                    disabled={annuelStatus?.statut === 'en_cours'}
                    onChange={(e) => handleFileSelectedAnnuel(e.target.files?.[0])}
                  />
                </label>
              </div>
            </details>

            <details className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/40 p-4">
              <summary className="text-sm font-semibold text-slate-600 dark:text-slate-300 cursor-pointer">
                J'ai un fichier avec les 12 mois déjà en colonnes (mappage manuel)
              </summary>
              <div className="mt-3 space-y-4">
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Pour une pharmacie dont l'export historique n'a pas le même format que le fichier Logpharma standard
                  — un seul fichier avec une colonne par mois. Vous indiquez une fois quelle colonne correspond à quoi.
                </p>

                {mappageError && (
                  <p className="text-xs text-danger">{mappageError}</p>
                )}

                {mappageImporting && (
                  <p className="text-xs text-slate-500 dark:text-slate-400">Import en cours…</p>
                )}

                {!mappageImporting && mappageStep === 1 && (
                  <label className="tg-tap inline-block rounded-lg border border-slate-400 dark:border-slate-500 px-3 py-1.5 text-sm font-medium text-slate-600 dark:text-slate-300 cursor-pointer transition hover:bg-white dark:hover:bg-slate-800">
                    {mappageLoadingStep ? 'Lecture en cours…' : 'Choisir le fichier'}
                    <input
                      type="file"
                      accept=".xlsx,.xls,.csv"
                      className="hidden"
                      disabled={mappageLoadingStep}
                      onChange={(e) => handleMappageFileSelected(e.target.files?.[0])}
                    />
                  </label>
                )}

                {!mappageImporting && mappageStep === 2 && (
                  <div className="space-y-3">
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Fichier : <span className="font-medium text-slate-700 dark:text-slate-300">{mappageFile?.name}</span>
                    </p>
                    {mappageAutoMapped && (
                      <p className="rounded-lg bg-info-light dark:bg-info/10 border border-info/30 text-info text-xs px-3 py-2">
                        Mappage détecté automatiquement — vérifiez et corrigez si besoin.
                      </p>
                    )}
                    {mappageChampsARevoir.length > 0 && (
                      <p className="rounded-lg bg-orange-50 dark:bg-orange-500/10 border border-orange-300 dark:border-orange-500/40 text-orange-700 dark:text-orange-400 text-xs px-3 py-2">
                        Certaines colonnes ont changé depuis le dernier import — vérifiez les champs surlignés.
                      </p>
                    )}
                    <div className="space-y-2">
                      {mappageChampsCibles.map((champ) => {
                        const obligatoire = CHAMPS_OBLIGATOIRES.includes(champ)
                        const aRevoir = mappageChampsARevoir.includes(champ)
                        return (
                          <div key={champ} className="flex items-center gap-2">
                            <label className="w-48 shrink-0 text-xs font-medium text-slate-600 dark:text-slate-400">
                              {CHAMPS_LABELS[champ] || champ}
                              {obligatoire && <span className="text-danger"> *</span>}
                            </label>
                            <select
                              value={mappageMapping[champ] || ''}
                              onChange={(e) => updateMappageChamp(champ, e.target.value)}
                              className={`flex-1 rounded-lg border px-2 py-1.5 text-xs text-slate-900 dark:text-slate-100 shadow-sm focus:outline-none focus:ring-2 focus:ring-brand ${
                                aRevoir
                                  ? 'border-orange-400 dark:border-orange-500 bg-orange-50 dark:bg-orange-500/10'
                                  : 'border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900'
                              }`}
                            >
                              <option value="">— Non mappé —</option>
                              {mappageColonnes.map((col) => (
                                <option key={col} value={col}>{col}</option>
                              ))}
                            </select>
                          </div>
                        )
                      })}
                    </div>
                    <div className="flex items-center justify-between pt-1">
                      <button
                        onClick={handleMappageRestart}
                        className="tg-tap rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 transition-colors hover:bg-slate-50 dark:hover:bg-slate-700"
                      >
                        Annuler
                      </button>
                      <button
                        onClick={handleMappageSaveAndImport}
                        disabled={mappageLoadingStep || mappageIncomplet()}
                        className="tg-tap rounded-lg bg-brand-gradient px-3.5 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:shadow-brand disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {mappageLoadingStep ? 'Import en cours…' : "Sauvegarder et importer"}
                      </button>
                    </div>
                  </div>
                )}

                {!mappageImporting && mappageStep === 3 && mappageResult && (
                  <div className="space-y-3">
                    <div className="flex gap-3">
                      <div className="flex-1 rounded-lg bg-brand-light dark:bg-brand/10 border border-brand/30 px-3 py-2 text-center">
                        <p className="text-lg font-semibold text-brand-dark dark:text-brand">{mappageResult.nb_lignes_ok ?? 0}</p>
                        <p className="text-[11px] text-brand-dark dark:text-brand">lignes importées</p>
                      </div>
                      <div className="flex-1 rounded-lg bg-orange-50 dark:bg-orange-500/10 border border-orange-300 dark:border-orange-500/40 px-3 py-2 text-center">
                        <p className="text-lg font-semibold text-orange-600 dark:text-orange-400">{mappageResult.nb_lignes_erreur ?? 0}</p>
                        <p className="text-[11px] text-orange-600 dark:text-orange-400">lignes en erreur</p>
                      </div>
                    </div>
                    {mappageCalculResult && (
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        {mappageCalculResult.nb_references} références recalculées — {mappageCalculResult.nb_a_commander} à commander
                      </p>
                    )}
                    {mappageResult.nb_lignes_erreur > 0 && (
                      <div>
                        <button
                          onClick={() => setMappageShowErreurs((prev) => !prev)}
                          className="tg-tap inline-flex items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 transition-colors hover:bg-slate-50 dark:hover:bg-slate-700"
                        >
                          {mappageShowErreurs ? 'Masquer les erreurs' : 'Voir les erreurs'}
                          <svg viewBox="0 0 16 16" className={`w-3.5 h-3.5 transition-transform ${mappageShowErreurs ? 'rotate-180' : ''}`} fill="none" aria-hidden="true">
                            <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        </button>
                        {mappageShowErreurs && (
                          <ul className="mt-2 space-y-1 max-h-48 overflow-y-auto text-xs">
                            {(mappageResult.erreurs_detail ? JSON.parse(mappageResult.erreurs_detail) : []).map((e, i) => (
                              <li key={i} className="rounded bg-white dark:bg-slate-900/60 px-2 py-1.5 text-slate-600 dark:text-slate-300">
                                {e.ligne ? `Ligne ${e.ligne} — ` : ''}{e.raison}
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}
                    <button
                      onClick={handleMappageRestart}
                      className="tg-tap inline-flex items-center gap-1.5 rounded-lg border border-brand px-3 py-1.5 text-xs font-semibold text-brand transition-colors hover:bg-brand-light dark:hover:bg-brand/10"
                    >
                      Importer un autre fichier
                    </button>
                  </div>
                )}
              </div>
            </details>

            <div className="flex items-center justify-between pt-2">
              <button
                onClick={handleRestart}
                className="tg-tap inline-flex items-center gap-1 rounded-lg border border-slate-200 dark:border-slate-700 px-3.5 py-2 text-sm font-medium text-slate-500 dark:text-slate-400 transition-colors hover:bg-slate-50 dark:hover:bg-slate-700"
              >
                ← Retour
              </button>
              <button
                onClick={() => {
                  marquerDirection('/import', '/dashboard')
                  navigate('/dashboard', { viewTransition: true })
                }}
                className="tg-tap rounded-lg bg-brand-gradient px-4 py-2.5 font-semibold text-white shadow-sm transition-all hover:shadow-brand hover:-translate-y-0.5"
              >
                Voir le tableau de bord
              </button>
            </div>
          </div>
        )}

        {!importing && typeImport === 'commande' && step === 1 && (
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
            <button
              onClick={handleRestart}
              className="tg-tap mx-auto mt-4 inline-flex items-center gap-1 rounded-lg border border-slate-200 dark:border-slate-700 px-3.5 py-2 text-sm font-medium text-slate-500 dark:text-slate-400 transition-colors hover:bg-slate-50 dark:hover:bg-slate-700"
            >
              ← Retour
            </button>
          </div>
        )}

        {!importing && typeImport === 'commande' && step === 3 && importResult && (
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

            <div className="flex items-center justify-between flex-wrap gap-2">
              <p className="text-sm text-slate-500 dark:text-slate-400">Stocks mis à jour et recommandations recalculées.</p>
              <button
                type="button"
                onClick={() => { marquerDirection('/import', '/quoi-commander'); navigate('/quoi-commander', { viewTransition: true }) }}
                className="tg-tap inline-flex items-center gap-1.5 rounded-lg border border-brand px-3.5 py-2 text-sm font-semibold text-brand transition-colors hover:bg-brand-light dark:hover:bg-brand/10"
              >
                Voir quoi commander
                <svg viewBox="0 0 16 16" className="w-3.5 h-3.5" fill="none" aria-hidden="true">
                  <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </div>

            {importResult.sorties_totales != null && (
              <p className="text-xs text-slate-400 dark:text-slate-500">
                {new Intl.NumberFormat('fr-FR').format(importResult.sorties_totales)} unités vendues au total sur cette période, toutes références confondues.
              </p>
            )}

            {importResult.nb_lignes_erreur > 0 && (
              <div>
                <button
                  onClick={() => setShowErreurs((prev) => !prev)}
                  className="tg-tap inline-flex items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-600 px-3.5 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 transition-colors hover:bg-slate-50 dark:hover:bg-slate-700"
                >
                  {showErreurs ? 'Masquer les erreurs' : 'Voir les erreurs'}
                  <svg viewBox="0 0 16 16" className={`w-3.5 h-3.5 transition-transform ${showErreurs ? 'rotate-180' : ''}`} fill="none" aria-hidden="true">
                    <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
                {showErreurs && (
                  <ul className="mt-3 space-y-1 max-h-64 overflow-y-auto text-sm">
                    {erreursDetail.map((e, i) => (
                      <li key={i} className="rounded bg-slate-50 dark:bg-slate-900/60 px-3 py-2 text-slate-600 dark:text-slate-300">
                        {e.ligne ? `Ligne ${e.ligne} — ` : ''}{e.raison}
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
