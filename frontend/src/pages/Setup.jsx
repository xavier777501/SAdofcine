import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Logo from '../components/Logo'
import ThemeToggle from '../components/ThemeToggle'
import FormField from '../components/FormField'
import ErrorBanner from '../components/ErrorBanner'
import SubmitButton from '../components/SubmitButton'
import { setup, getErrorMessage } from '../services/auth'
import { marquerDirection } from '../services/pageTransition'

const MIN_PASSWORD_LENGTH = 8

export default function Setup() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '', officineNom: '' })
  const [fieldErrors, setFieldErrors] = useState({})
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function update(field) {
    return (e) => setForm((prev) => ({ ...prev, [field]: e.target.value }))
  }

  function validate() {
    const errors = {}
    if (!form.officineNom.trim()) {
      errors.officineNom = 'Indiquez le nom de votre pharmacie.'
    }
    if (form.password.length < MIN_PASSWORD_LENGTH) {
      errors.password = `Le mot de passe doit contenir au moins ${MIN_PASSWORD_LENGTH} caractères.`
    }
    return errors
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    const errors = validate()
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setLoading(true)
    try {
      await setup(form)
      marquerDirection('/setup', '/dashboard')
      navigate('/dashboard', { replace: true, viewTransition: true })
    } catch (err) {
      setError(getErrorMessage(err, 'Impossible de configurer l\'application. Réessayez.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen relative bg-surface dark:bg-slate-900 flex flex-col items-center justify-center px-4 py-10">
      <ThemeToggle className="absolute top-4 right-4" />
      <div className="text-center mb-6">
        <Logo className="h-14 w-14 mx-auto mb-3 rounded-xl shadow-md" />
        <h1 className="brand-name text-4xl text-brand">StockAid</h1>
      </div>
      <div className="w-full max-w-md bg-white dark:bg-slate-800 rounded-2xl shadow-lg border border-slate-200 dark:border-slate-700 p-8">
        <h2 className="text-2xl font-semibold text-slate-900 dark:text-slate-100 text-center mb-1">Créer un compte</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 text-center mb-6">
          C'est rapide et simple — cette étape n'apparaît qu'une seule fois.
        </p>
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <ErrorBanner message={error} />
          <FormField
            label="Nom de la pharmacie"
            id="officineNom"
            type="text"
            autoComplete="organization"
            required
            placeholder="Ex : Pharmacie Centrale"
            value={form.officineNom}
            onChange={update('officineNom')}
            error={fieldErrors.officineNom}
          />
          <FormField
            label="Email"
            id="email"
            type="email"
            autoComplete="email"
            required
            value={form.email}
            onChange={update('email')}
          />
          <FormField
            label="Mot de passe"
            id="password"
            type="password"
            autoComplete="new-password"
            required
            minLength={MIN_PASSWORD_LENGTH}
            hint="8 caractères minimum — vous pourrez le modifier dans les réglages"
            value={form.password}
            onChange={update('password')}
            error={fieldErrors.password}
          />
          <hr className="border-slate-200 dark:border-slate-700" />
          <SubmitButton loading={loading}>Créer un compte</SubmitButton>
        </form>
      </div>
    </div>
  )
}
