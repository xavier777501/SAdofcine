import { useEffect, useState } from 'react'
import ErrorBanner from '../components/ErrorBanner'
import FormField from '../components/FormField'
import SubmitButton from '../components/SubmitButton'
import { getErrorMessage } from '../services/auth'
import { getParametres, updateParametres, CYCLE_OPTIONS } from '../services/parametres'

function versFormulaire(params) {
  return {
    dl_moy_jours: String(params.dl_moy_jours),
    dl_max_jours: String(params.dl_max_jours),
    cycle_commande_jours: String(params.cycle_commande_jours),
    cout_commande: String(params.cout_commande),
    taux_detention_pct: String(Math.round(params.taux_detention * 100)),
  }
}

export default function Reglages() {
  const [form, setForm] = useState(null)
  const [fieldErrors, setFieldErrors] = useState({})
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    getParametres()
      .then((params) => setForm(versFormulaire(params)))
      .catch((err) => setError(getErrorMessage(err, 'Impossible de charger les réglages.')))
      .finally(() => setLoading(false))
  }, [])

  function update(champ) {
    return (e) => setForm((prev) => ({ ...prev, [champ]: e.target.value }))
  }

  function validate() {
    const errors = {}
    const dlMoy = Number(form.dl_moy_jours)
    const dlMax = Number(form.dl_max_jours)
    const cout = Number(form.cout_commande)
    const tauxPct = Number(form.taux_detention_pct)

    if (!dlMoy || dlMoy <= 0) errors.dl_moy_jours = 'Indiquez un délai moyen supérieur à 0.'
    if (!dlMax || dlMax <= 0) errors.dl_max_jours = 'Indiquez un délai maximum supérieur à 0.'
    if (dlMoy && dlMax && dlMax < dlMoy) {
      errors.dl_max_jours = 'Le délai maximum doit être supérieur ou égal au délai moyen.'
    }
    if (!cout || cout <= 0) errors.cout_commande = 'Indiquez un coût supérieur à 0.'
    if (!tauxPct || tauxPct <= 0 || tauxPct >= 100) {
      errors.taux_detention_pct = 'Indiquez un pourcentage entre 0 et 100.'
    }
    return errors
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSuccess(false)
    const errors = validate()
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setSaving(true)
    try {
      const params = await updateParametres({
        dl_moy_jours: Number(form.dl_moy_jours),
        dl_max_jours: Number(form.dl_max_jours),
        cycle_commande_jours: Number(form.cycle_commande_jours),
        cout_commande: Number(form.cout_commande),
        taux_detention: Number(form.taux_detention_pct) / 100,
      })
      setForm(versFormulaire(params))
      setSuccess(true)
    } catch (err) {
      setError(getErrorMessage(err, 'Impossible d\'enregistrer les réglages.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="px-6 py-8 md:px-10 md:py-10 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">Réglages</h1>
        <p className="mt-1 text-slate-500 dark:text-slate-400 text-sm">
          Ces valeurs servent à calculer vos recommandations de commande. Elles changent rarement.
        </p>
      </div>

        <ErrorBanner message={error} />
        {success && (
          <p className="rounded-lg bg-brand-light dark:bg-brand/10 border border-brand/30 text-brand-dark dark:text-brand text-sm px-4 py-3">
            Réglages enregistrés — vos recommandations ont été recalculées automatiquement.
          </p>
        )}

        {loading ? (
          <p className="text-sm text-slate-400 dark:text-slate-500">Chargement…</p>
        ) : (
          <form
            onSubmit={handleSubmit}
            className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-6 space-y-5"
          >
            <div className="grid grid-cols-2 gap-4">
              <FormField
                label="Délai moyen fournisseur (jours)"
                id="dl_moy_jours"
                type="number"
                min="1"
                required
                hint="Temps habituel de livraison depuis la commande"
                value={form.dl_moy_jours}
                onChange={update('dl_moy_jours')}
                error={fieldErrors.dl_moy_jours}
              />
              <FormField
                label="Délai maximum fournisseur (jours)"
                id="dl_max_jours"
                type="number"
                min="1"
                required
                hint="Le pire cas observé, en cas de retard"
                value={form.dl_max_jours}
                onChange={update('dl_max_jours')}
                error={fieldErrors.dl_max_jours}
              />
            </div>

            <div className="text-left">
              <label htmlFor="cycle" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Rythme de commande
              </label>
              <select
                id="cycle"
                value={form.cycle_commande_jours}
                onChange={update('cycle_commande_jours')}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-3 py-2 text-slate-900 dark:text-slate-100 shadow-sm focus:outline-none focus:ring-2 focus:ring-brand"
              >
                {CYCLE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                À quelle fréquence vous groupez vos commandes chez le grossiste
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <FormField
                label="Coût d'une commande (FCFA)"
                id="cout_commande"
                type="number"
                min="1"
                required
                hint="Frais fixes à chaque commande passée"
                value={form.cout_commande}
                onChange={update('cout_commande')}
                error={fieldErrors.cout_commande}
              />
              <FormField
                label="Taux de détention du stock (%)"
                id="taux_detention_pct"
                type="number"
                min="1"
                max="99"
                required
                hint="Coût annuel de stockage, en % de la valeur du stock"
                value={form.taux_detention_pct}
                onChange={update('taux_detention_pct')}
                error={fieldErrors.taux_detention_pct}
              />
            </div>

            <SubmitButton loading={saving}>Enregistrer les réglages</SubmitButton>
          </form>
        )}
    </div>
  )
}
