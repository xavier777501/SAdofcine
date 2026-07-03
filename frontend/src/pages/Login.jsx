import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import AuthLayout from '../components/AuthLayout'
import FormField from '../components/FormField'
import ErrorBanner from '../components/ErrorBanner'
import SubmitButton from '../components/SubmitButton'
import { login, getErrorMessage } from '../services/auth'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const successMessage = location.state?.registered
    ? 'Compte créé avec succès. Connectez-vous pour continuer.'
    : ''

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login({ email, password })
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(getErrorMessage(err, 'Mot de passe incorrect ou email inconnu.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Se connecter" subtitle="Accédez au tableau de bord de votre pharmacie">
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {successMessage && (
          <div className="rounded-lg bg-green-50 border border-green-200 text-green-700 text-sm px-4 py-3">
            {successMessage}
          </div>
        )}
        <ErrorBanner message={error} />
        <FormField
          label="Email"
          id="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <FormField
          label="Mot de passe"
          id="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <SubmitButton loading={loading}>Se connecter</SubmitButton>
      </form>
      <p className="mt-6 text-center text-sm text-slate-500">
        Pas encore de compte ?{' '}
        <Link to="/register" className="font-medium text-amber-600 hover:underline">
          Créer mon compte pharmacie
        </Link>
      </p>
    </AuthLayout>
  )
}
