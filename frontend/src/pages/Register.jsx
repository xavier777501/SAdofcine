import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import AuthLayout from '../components/AuthLayout'
import FormField from '../components/FormField'
import ErrorBanner from '../components/ErrorBanner'
import SubmitButton from '../components/SubmitButton'
import { register, getErrorMessage } from '../services/auth'

const MIN_PASSWORD_LENGTH = 8

export default function Register() {
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
      await register(form)
      navigate('/login', { state: { registered: true }, replace: true })
    } catch (err) {
      setError(getErrorMessage(err, 'Impossible de créer le compte. Réessayez.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Créer mon compte pharmacie" subtitle="Quelques informations pour démarrer">
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <ErrorBanner message={error} />
        <FormField
          label="Nom de la pharmacie"
          id="officineNom"
          type="text"
          autoComplete="organization"
          required
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
          hint="8 caractères minimum"
          value={form.password}
          onChange={update('password')}
          error={fieldErrors.password}
        />
        <SubmitButton loading={loading}>Créer mon compte pharmacie</SubmitButton>
      </form>
      <p className="mt-6 text-center text-sm text-slate-500">
        Déjà un compte ?{' '}
        <Link to="/login" className="font-medium text-amber-600 hover:underline">
          Se connecter
        </Link>
      </p>
    </AuthLayout>
  )
}
