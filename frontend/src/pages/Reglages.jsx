import { useEffect, useState } from 'react'
import ErrorBanner from '../components/ErrorBanner'
import FormField from '../components/FormField'
import SubmitButton from '../components/SubmitButton'
import PageHeader from '../components/PageHeader'
import { getErrorMessage } from '../services/auth'
import { getParametres, updateParametres, getCircuits, updateDelaiCircuit, CYCLE_OPTIONS } from '../services/parametres'

function versFormulaire(params) {
  return {
    dl_moy_jours: String(params.dl_moy_jours),
    dl_max_jours: String(params.dl_max_jours),
    cycle_commande_jours: String(params.cycle_commande_jours),
    cout_commande: String(params.cout_commande),
    taux_detention_pct: String(Math.round(params.taux_detention * 100)),
    niveau_service_vital_pct: String(Math.round(params.niveau_service_vital * 100)),
    niveau_service_essentiel_pct: String(Math.round(params.niveau_service_essentiel * 100)),
    niveau_service_desirable_pct: String(Math.round(params.niveau_service_desirable * 100)),
    niveau_service_non_renseigne_pct: String(Math.round(params.niveau_service_non_renseigne * 100)),
    plafond_commande_fcfa: params.plafond_commande_fcfa != null ? String(params.plafond_commande_fcfa) : '',
    notification_active: params.notification_active,
    notification_heure: params.notification_heure,
    notification_email: params.notification_email || '',
  }
}

function CircuitRow({ circuit, onSaved }) {
  const [dlMoy, setDlMoy] = useState(String(circuit.dl_moy_jours))
  const [dlMax, setDlMax] = useState(String(circuit.dl_max_jours))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function handleSave() {
    setError('')
    const moy = Number(dlMoy)
    const max = Number(dlMax)
    if (!moy || moy <= 0 || !max || max <= 0) {
      setError('Indiquez des délais supérieurs à 0.')
      return
    }
    if (max < moy) {
      setError('Le délai maximum doit être ≥ au délai moyen.')
      return
    }
    setSaving(true)
    try {
      const updated = await updateDelaiCircuit(circuit.circuit, { dlMoyJours: moy, dlMaxJours: max })
      onSaved(updated)
    } catch (err) {
      setError(getErrorMessage(err, 'Impossible d\'enregistrer ce circuit.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-3 py-3 border-b border-slate-100 dark:border-slate-700 last:border-0">
      <div className="min-w-[140px] flex-1">
        <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{circuit.circuit}</p>
        {!circuit.configure && (
          <p className="text-xs text-slate-400 dark:text-slate-500">Utilise le délai global pour l'instant</p>
        )}
      </div>
      <div className="flex items-center gap-1.5">
        <input
          type="number" min="1" value={dlMoy} onChange={(e) => setDlMoy(e.target.value)}
          className="w-16 text-sm text-right rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5 text-slate-900 dark:text-slate-100 focus:outline-none focus:border-brand"
        />
        <span className="text-xs text-slate-400">j moy.</span>
      </div>
      <div className="flex items-center gap-1.5">
        <input
          type="number" min="1" value={dlMax} onChange={(e) => setDlMax(e.target.value)}
          className="w-16 text-sm text-right rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5 text-slate-900 dark:text-slate-100 focus:outline-none focus:border-brand"
        />
        <span className="text-xs text-slate-400">j max.</span>
      </div>
      <button
        type="button"
        onClick={handleSave}
        disabled={saving}
        className="tg-tap rounded-lg border border-brand text-brand px-3 py-1.5 text-xs font-semibold hover:bg-brand-light dark:hover:bg-brand/10 transition-colors disabled:opacity-50"
      >
        {saving ? 'Enregistrement…' : 'Enregistrer'}
      </button>
      {error && <p className="w-full text-xs text-danger">{error}</p>}
    </div>
  )
}

export default function Reglages() {
  const [form, setForm] = useState(null)
  const [fieldErrors, setFieldErrors] = useState({})
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [circuits, setCircuits] = useState([])
  const [circuitsChargement, setCircuitsChargement] = useState(true)

  useEffect(() => {
    getParametres()
      .then((params) => setForm(versFormulaire(params)))
      .catch((err) => setError(getErrorMessage(err, 'Impossible de charger les réglages.')))
      .finally(() => setLoading(false))

    getCircuits()
      .then(setCircuits)
      .catch(() => setCircuits([]))
      .finally(() => setCircuitsChargement(false))
  }, [])

  function update(champ) {
    return (e) => setForm((prev) => ({ ...prev, [champ]: e.target.value }))
  }

  function toggle(champ) {
    return (e) => setForm((prev) => ({ ...prev, [champ]: e.target.checked }))
  }

  function handleCircuitSaved(updated) {
    setCircuits((prev) => prev.map((c) => (c.circuit === updated.circuit ? updated : c)))
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
    for (const champ of ['niveau_service_vital_pct', 'niveau_service_essentiel_pct', 'niveau_service_desirable_pct', 'niveau_service_non_renseigne_pct']) {
      const v = Number(form[champ])
      if (!v || v <= 0 || v >= 100) errors[champ] = 'Indiquez un pourcentage entre 0 et 100.'
    }
    if (form.plafond_commande_fcfa.trim() !== '' && Number(form.plafond_commande_fcfa) < 0) {
      errors.plafond_commande_fcfa = 'Indiquez un montant positif, ou laissez vide pour ne pas limiter.'
    }
    if (form.notification_active && !/^\d{2}:\d{2}$/.test(form.notification_heure)) {
      errors.notification_heure = 'Indiquez une heure au format HH:MM.'
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
        niveau_service_vital: Number(form.niveau_service_vital_pct) / 100,
        niveau_service_essentiel: Number(form.niveau_service_essentiel_pct) / 100,
        niveau_service_desirable: Number(form.niveau_service_desirable_pct) / 100,
        niveau_service_non_renseigne: Number(form.niveau_service_non_renseigne_pct) / 100,
        plafond_commande_fcfa: form.plafond_commande_fcfa.trim() === '' ? null : Number(form.plafond_commande_fcfa),
        notification_active: form.notification_active,
        notification_heure: form.notification_heure,
        notification_email: form.notification_email.trim() === '' ? null : form.notification_email.trim(),
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
      <PageHeader
        label="Réglages"
        title="Réglages"
        subtitle="Ces valeurs servent à calculer vos recommandations de commande. Elles changent rarement."
      />

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

            <hr className="border-slate-200 dark:border-slate-700" />

            <div>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Niveau de service souhaité</p>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Plus le pourcentage est élevé, moins vous risquez la rupture — mais plus le stock de sécurité immobilise de trésorerie.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <FormField
                label="Produits vitaux (%)"
                id="niveau_service_vital_pct"
                type="number"
                min="1"
                max="99"
                required
                value={form.niveau_service_vital_pct}
                onChange={update('niveau_service_vital_pct')}
                error={fieldErrors.niveau_service_vital_pct}
              />
              <FormField
                label="Produits essentiels (%)"
                id="niveau_service_essentiel_pct"
                type="number"
                min="1"
                max="99"
                required
                value={form.niveau_service_essentiel_pct}
                onChange={update('niveau_service_essentiel_pct')}
                error={fieldErrors.niveau_service_essentiel_pct}
              />
              <FormField
                label="Produits désirables (%)"
                id="niveau_service_desirable_pct"
                type="number"
                min="1"
                max="99"
                required
                value={form.niveau_service_desirable_pct}
                onChange={update('niveau_service_desirable_pct')}
                error={fieldErrors.niveau_service_desirable_pct}
              />
              <FormField
                label="Produits non classés (%)"
                id="niveau_service_non_renseigne_pct"
                type="number"
                min="1"
                max="99"
                required
                hint="Tant qu'un produit n'a pas été classé"
                value={form.niveau_service_non_renseigne_pct}
                onChange={update('niveau_service_non_renseigne_pct')}
                error={fieldErrors.niveau_service_non_renseigne_pct}
              />
            </div>

            <hr className="border-slate-200 dark:border-slate-700" />

            <div>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Plafond budgétaire de commande</p>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Montant maximum pour une session de commande. Les produits vitaux en rupture sont toujours inclus,
                même au-delà de ce montant. Laissez vide pour ne fixer aucune limite.
              </p>
            </div>

            <FormField
              label="Plafond (FCFA)"
              id="plafond_commande_fcfa"
              type="number"
              min="0"
              hint="Optionnel — vide ou 0 = pas de limite"
              value={form.plafond_commande_fcfa}
              onChange={update('plafond_commande_fcfa')}
              error={fieldErrors.plafond_commande_fcfa}
            />

            <hr className="border-slate-200 dark:border-slate-700" />

            <div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.notification_active}
                  onChange={toggle('notification_active')}
                  className="w-4 h-4 rounded border-slate-300 dark:border-slate-600 text-brand focus:ring-brand"
                />
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Notification quotidienne par e-mail</span>
              </label>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Un e-mail résumant les références stratégiques manquées (encart en haut de "Quoi commander"), envoyé une fois par jour dès que vous ouvrez StockAid après l'heure choisie — pas d'heure garantie à la minute, StockAid ne tournant pas en permanence.
              </p>
            </div>

            {form.notification_active && (
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  label="Heure d'envoi"
                  id="notification_heure"
                  type="time"
                  value={form.notification_heure}
                  onChange={update('notification_heure')}
                  error={fieldErrors.notification_heure}
                />
                <FormField
                  label="E-mail destinataire"
                  id="notification_email"
                  type="email"
                  hint="Vide = e-mail de votre compte"
                  value={form.notification_email}
                  onChange={update('notification_email')}
                />
              </div>
            )}

            <SubmitButton loading={saving} loadingLabel="Recalcul en cours… (peut prendre 20 s)">
              Enregistrer les réglages
            </SubmitButton>
          </form>
        )}

        {!circuitsChargement && circuits.length > 0 && (
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Délais par circuit fournisseur</p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Vos références importées viennent de plusieurs circuits (local, France, Chine-Inde...). Vous pouvez donner un délai spécifique à chacun — sinon le délai global ci-dessus s'applique.
            </p>
            <div className="mt-3">
              {circuits.map((c) => (
                <CircuitRow key={c.circuit} circuit={c} onSaved={handleCircuitSaved} />
              ))}
            </div>
          </div>
        )}
    </div>
  )
}
