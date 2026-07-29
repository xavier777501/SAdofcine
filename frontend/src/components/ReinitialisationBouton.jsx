import { useState } from 'react'
import { getErrorMessage } from '../services/auth'

/**
 * Bouton de réinitialisation partielle réutilisable (historique, stock...),
 * avec confirmation par mot de passe — même garde-fou que la réinitialisation
 * complète (Réglages), pour une action toujours irréversible même si son
 * périmètre est plus restreint.
 */
export default function ReinitialisationBouton({ label, description, messageSucces, onConfirmer, onSucces }) {
  const [ouvert, setOuvert] = useState(false)
  const [motDePasse, setMotDePasse] = useState('')
  const [confirme, setConfirme] = useState(false)
  const [enCours, setEnCours] = useState(false)
  const [erreur, setErreur] = useState('')
  const [termine, setTermine] = useState(false)

  async function handleConfirmer() {
    setErreur('')
    setEnCours(true)
    try {
      await onConfirmer(motDePasse)
      setTermine(true)
      onSucces?.()
    } catch (err) {
      setErreur(getErrorMessage(err, 'Impossible de réinitialiser — vérifiez votre mot de passe.'))
    } finally {
      setEnCours(false)
    }
  }

  if (termine) {
    return (
      <p className="text-sm font-semibold text-danger">{messageSucces}</p>
    )
  }

  if (!ouvert) {
    return (
      <button
        type="button"
        onClick={() => setOuvert(true)}
        className="tg-tap rounded-lg border border-danger/40 text-danger px-3.5 py-2 text-xs font-semibold hover:bg-danger-light dark:hover:bg-danger/10 transition-colors"
      >
        {label}
      </button>
    )
  }

  return (
    <div className="rounded-xl border border-danger/30 bg-danger-light dark:bg-danger/10 p-4 space-y-3">
      <p className="text-xs text-danger">{description}</p>
      {erreur && <p className="text-xs text-danger font-semibold">{erreur}</p>}
      <input
        type="password"
        placeholder="Votre mot de passe"
        value={motDePasse}
        onChange={(e) => setMotDePasse(e.target.value)}
        className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-danger"
      />
      <label className="flex items-start gap-2 text-xs text-slate-600 dark:text-slate-300">
        <input type="checkbox" checked={confirme} onChange={(e) => setConfirme(e.target.checked)} className="mt-0.5" />
        Je comprends que cette action est irréversible.
      </label>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={handleConfirmer}
          disabled={!motDePasse || !confirme || enCours}
          className="tg-tap rounded-lg bg-danger px-3.5 py-2 text-xs font-semibold text-white shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {enCours ? 'Réinitialisation…' : 'Confirmer'}
        </button>
        <button
          type="button"
          onClick={() => { setOuvert(false); setMotDePasse(''); setConfirme(false); setErreur('') }}
          className="tg-tap rounded-lg border border-slate-300 dark:border-slate-600 px-3.5 py-2 text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700"
        >
          Annuler
        </button>
      </div>
    </div>
  )
}
