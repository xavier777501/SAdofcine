import { useState } from 'react'
import PageHeader from '../components/PageHeader'
import ImportHistoryTable from '../components/ImportHistoryTable'
import { runImportReception } from '../services/imports'
import { reinitialiserStock } from '../services/parametres'
import ReinitialisationBouton from '../components/ReinitialisationBouton'

export default function Reapprovisionnement() {
  const [fichier, setFichier] = useState(null)
  const [enCours, setEnCours] = useState(false)
  const [resultat, setResultat] = useState(null)
  const [erreur, setErreur] = useState('')
  const [afficherErreurs, setAfficherErreurs] = useState(false)

  function choisirFichier(f) {
    setFichier(f || null)
    setResultat(null)
    setErreur('')
    setAfficherErreurs(false)
  }

  async function lancerImport() {
    if (!fichier) return
    setEnCours(true)
    setErreur('')
    setResultat(null)
    try {
      const data = await runImportReception(fichier)
      setResultat(data)
    } catch (err) {
      setErreur(
        err?.response?.data?.detail ||
        "Impossible de lire ce fichier — vérifiez que c'est bien un bon de livraison Logpharma.",
      )
    } finally {
      setEnCours(false)
    }
  }

  const erreursDetail = resultat?.erreurs_detail ? JSON.parse(resultat.erreurs_detail) : []

  return (
    <div className="px-6 py-8 md:px-10 md:py-10 max-w-3xl mx-auto space-y-6">
      <PageHeader
        label="Réapprovisionnement"
        title="Mettre à jour le réapprovisionnement"
        subtitle="À chaque livraison reçue d'un fournisseur, pour ne jamais recommander un produit déjà réapprovisionné."
      />

      <div className="rounded-xl bg-info-light dark:bg-info/10 border border-info/30 px-5 py-4">
        <p className="text-sm font-semibold text-info">Ceci ne touche jamais vos calculs de fond.</p>
        <p className="mt-1 text-xs text-info/90">
          Cet écran met seulement à jour le stock actuel des produits livrés, à partir du bon de livraison Logpharma
          (fichier Word). Les ventes moyennes, classes et priorités restent celles calculées par l'historique mensuel —
          utilisez "Mettre à jour l'historique mensuel" pour ça.
        </p>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-6 space-y-4">
        <div>
          <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">Bon de livraison</p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            Le fichier Word que Logpharma génère à chaque réception de livraison. Vous pouvez importer plusieurs
            livraisons de fournisseurs différents à la suite, une par une.
          </p>
        </div>

        <label className="tg-tap flex items-center justify-center gap-2 rounded-xl border-2 border-dashed border-slate-300 dark:border-slate-600 px-5 py-8 cursor-pointer transition-colors hover:border-brand hover:bg-brand-light/40 dark:hover:bg-brand/5">
          <svg viewBox="0 0 24 24" className="w-5 h-5 text-slate-400" fill="none" aria-hidden="true">
            <path d="M12 15V4m0 0 4 4m-4-4-4 4M5 15v3a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="text-sm text-slate-600 dark:text-slate-300">
            {fichier ? fichier.name : 'Choisir le fichier du bon de livraison'}
          </span>
          <input
            type="file"
            accept=".doc,.docx,.rtf"
            className="hidden"
            disabled={enCours}
            onChange={(e) => choisirFichier(e.target.files?.[0])}
          />
        </label>

        <button
          type="button"
          onClick={lancerImport}
          disabled={!fichier || enCours}
          className="tg-tap w-full rounded-lg bg-brand-gradient px-4 py-2.5 font-semibold text-white shadow-sm transition-all hover:shadow-brand disabled:cursor-not-allowed disabled:opacity-60"
        >
          {enCours ? 'Import en cours…' : 'Mettre à jour les stocks'}
        </button>

        {erreur && (
          <p className="rounded-lg bg-danger-light dark:bg-danger/10 border border-danger/30 text-danger text-sm px-4 py-3">
            {erreur}
          </p>
        )}

        {resultat && (
          <div className="rounded-xl bg-brand-light dark:bg-brand/10 border border-brand/30 px-5 py-4 space-y-3">
            <p className="text-sm font-semibold text-brand-dark dark:text-brand">
              {resultat.fournisseur ? `Livraison de ${resultat.fournisseur} traitée` : 'Livraison traitée'}
            </p>
            <div className="flex gap-6">
              <div>
                <p className="text-2xl font-semibold text-brand-dark dark:text-brand">{resultat.nb_lignes_ok ?? 0}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">Stocks mis à jour</p>
              </div>
              {resultat.nb_lignes_erreur > 0 && (
                <div>
                  <p className="text-2xl font-semibold text-orange-600 dark:text-orange-400">{resultat.nb_lignes_erreur}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Codes non reconnus</p>
                </div>
              )}
            </div>

            {resultat.nb_lignes_erreur > 0 && (
              <div>
                <button
                  type="button"
                  onClick={() => setAfficherErreurs((prev) => !prev)}
                  className="tg-tap inline-flex items-center gap-1.5 rounded-lg border border-slate-300 dark:border-slate-600 px-3.5 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 transition-colors hover:bg-slate-50 dark:hover:bg-slate-700"
                >
                  {afficherErreurs ? 'Masquer les erreurs' : 'Voir les erreurs'}
                  <svg viewBox="0 0 16 16" className={`w-3.5 h-3.5 transition-transform ${afficherErreurs ? 'rotate-180' : ''}`} fill="none" aria-hidden="true">
                    <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
                {afficherErreurs && (
                  <ul className="mt-3 space-y-1 max-h-64 overflow-y-auto text-sm">
                    {erreursDetail.map((e, i) => (
                      <li key={i} className="rounded bg-white/70 dark:bg-slate-900/40 px-3 py-2 text-slate-600 dark:text-slate-300">
                        {e.ligne ? `Code ${e.ligne} — ` : ''}{e.raison}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      <ImportHistoryTable key={resultat?.id || 'aucun'} />

      <div className="flex justify-center">
        <ReinitialisationBouton
          label="Réinitialiser le stock…"
          description="Remet le stock actuel à 0 pour toutes vos références, efface le mode ciblé et les sorties de la dernière commande — comme si aucun import de commande ou de réception n'avait jamais été fait. Ne touche pas à l'historique."
          messageSucces="Stock réinitialisé — refaites un import de commande ou de réception."
          onConfirmer={reinitialiserStock}
        />
      </div>
    </div>
  )
}
