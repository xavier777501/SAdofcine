import { useEffect, useState, useCallback } from 'react'
import { getImportHistory } from '../services/imports'
import { reinitialiserJournal } from '../services/parametres'
import ReinitialisationBouton from './ReinitialisationBouton'

const STATUT_STYLES = {
  succes: 'bg-brand-light dark:bg-brand/10 text-brand-dark dark:text-brand border-brand/30',
  en_cours: 'bg-info-light dark:bg-info/10 text-info border-info/30',
  erreur: 'bg-danger-light dark:bg-danger/10 text-danger border-danger/30',
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

export default function ImportHistoryTable() {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)

  const charger = useCallback(() => {
    getImportHistory()
      .then(setHistory)
      .catch(() => setHistory([]))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { charger() }, [charger])

  return (
    <section>
      <div className="flex items-center justify-between gap-3 mb-3">
        <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Historique des imports</h2>
        {!loading && history.length > 0 && (
          <ReinitialisationBouton
            label="Vider l'historique…"
            description="Vide uniquement ce tableau — n'affecte ni le stock, ni l'historique 12 mois, ni aucun calcul."
            messageSucces="Historique vidé."
            onConfirmer={reinitialiserJournal}
            onSucces={charger}
          />
        )}
      </div>
      {loading ? (
        <p className="text-sm text-slate-400 dark:text-slate-500">Chargement…</p>
      ) : history.length === 0 ? (
        <p className="text-sm text-slate-400 dark:text-slate-500">Aucun import pour le moment.</p>
      ) : (
        <div className="overflow-x-auto bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700 text-left text-slate-500 dark:text-slate-400">
                <th className="px-4 py-2 font-medium">Date</th>
                <th className="px-4 py-2 font-medium">Fichier</th>
                <th className="px-4 py-2 font-medium">Statut</th>
                <th className="px-4 py-2 font-medium">Lignes OK</th>
                <th className="px-4 py-2 font-medium">Lignes erreur</th>
                <th className="px-4 py-2 font-medium">Fournisseur</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.id} className="border-b border-slate-100 dark:border-slate-700 last:border-0">
                  <td className="px-4 py-2 text-slate-600 dark:text-slate-300">{formatDate(h.created_at)}</td>
                  <td className="px-4 py-2 text-slate-900 dark:text-slate-100">{h.nom_fichier}</td>
                  <td className="px-4 py-2">
                    <span
                      className={`inline-block rounded-full border px-2 py-0.5 text-xs font-medium ${
                        STATUT_STYLES[h.statut] || 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 border-slate-300 dark:border-slate-600'
                      }`}
                    >
                      {h.statut}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-slate-600 dark:text-slate-300">{h.nb_lignes_ok ?? '—'}</td>
                  <td className="px-4 py-2 text-slate-600 dark:text-slate-300">{h.nb_lignes_erreur ?? '—'}</td>
                  <td className="px-4 py-2 text-slate-600 dark:text-slate-300">{h.fournisseur ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
