import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import AuthLayout from '../components/AuthLayout'
import FormField from '../components/FormField'
import ErrorBanner from '../components/ErrorBanner'
import SubmitButton from '../components/SubmitButton'
import { login, checkIsSetup, getErrorMessage } from '../services/auth'
import { marquerDirection } from '../services/pageTransition'

export default function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [notConfigured, setNotConfigured] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setNotConfigured(false)
    setLoading(true)
    try {
      await login({ email, password })
      marquerDirection('/login', '/dashboard')
      navigate('/dashboard', { replace: true, viewTransition: true })
    } catch (err) {
      const { configured } = await checkIsSetup().catch(() => ({ configured: true }))
      if (!configured) {
        setNotConfigured(true)
      } else {
        setError(getErrorMessage(err, 'Mot de passe incorrect ou email inconnu.'))
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Se connecter" subtitle="Accédez au tableau de bord de votre pharmacie">
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
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
      {notConfigured && (
        <Link
          to="/setup"
          viewTransition
          onClick={() => marquerDirection('/login', '/setup')}
          className="tg-tap mt-4 block w-full rounded-lg border border-brand px-4 py-2.5 text-center font-semibold text-brand transition hover:bg-brand-light dark:hover:bg-brand/10"
        >
          Créer un compte
        </Link>
      )}
    </AuthLayout>
  )
}
