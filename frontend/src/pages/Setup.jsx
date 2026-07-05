import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AuthLayout from '../components/AuthLayout'
import FormField from '../components/FormField'
import ErrorBanner from '../components/ErrorBanner'
import SubmitButton from '../components/SubmitButton'
import { setup, getErrorMessage } from '../services/auth'

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
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(getErrorMessage(err, 'Impossible de configurer l\'application. Réessayez.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout
      title="Bienvenue sur SAD OFFICINE"
      subtitle="Configurez votre application — cette étape n'apparaît qu'une seule fois"
    >
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
        <SubmitButton loading={loading}>Démarrer l'application</SubmitButton>
      </form>
    </AuthLayout>
  )
}
