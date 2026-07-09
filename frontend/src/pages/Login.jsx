import { useState, useEffect } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import AuthLayout from '../components/AuthLayout'
import ErrorBanner from '../components/ErrorBanner'
import SubmitButton from '../components/SubmitButton'
import { login, checkIsSetup, getErrorMessage } from '../services/auth'
import { marquerDirection } from '../services/pageTransition'

const inputClasses =
  'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-4 py-3 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 shadow-xs transition-shadow focus:outline-none focus:border-brand focus:shadow-[0_0_0_4px_var(--color-brand-light)]'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const motDePasseReinitialise = Boolean(location.state?.motDePasseReinitialise)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [notConfigured, setNotConfigured] = useState(false)
  const [loading, setLoading] = useState(false)
  const [afficherMotDePasse, setAfficherMotDePasse] = useState(false)

  useEffect(() => {
    checkIsSetup()
      .then(({ configured }) => setNotConfigured(!configured))
      .catch(() => {})
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setNotConfigured(false)
    setLoading(true)
    try {
      await login({ email, password })
      marquerDirection('/login', '/bienvenue')
      navigate('/bienvenue', { replace: true, viewTransition: true })
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

  const footer = notConfigured && (
    <>
      <hr className="my-6 border-slate-200 dark:border-slate-700" />
      <Link
        to="/setup"
        viewTransition
        onClick={() => marquerDirection('/login', '/setup')}
        className="tg-tap block w-full rounded-lg border border-brand px-4 py-2.5 text-center font-semibold text-brand transition hover:bg-brand-light dark:hover:bg-brand/10"
      >
        Créer un nouveau compte
      </Link>
    </>
  )

  return (
    <AuthLayout title="Se connecter à StockAid" footer={footer}>
      <form onSubmit={handleSubmit} className="space-y-3" noValidate>
        {motDePasseReinitialise && !error && (
          <div
            role="status"
            className="rounded-lg bg-brand-light dark:bg-brand/10 border border-brand/30 text-brand-dark dark:text-brand text-sm px-4 py-3 text-left"
          >
            Mot de passe réinitialisé — vous pouvez vous connecter.
          </div>
        )}
        <ErrorBanner message={error} />
        <div>
          <label htmlFor="email" className="sr-only">Email</label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            required
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={inputClasses}
          />
        </div>
        <div className="relative">
          <label htmlFor="password" className="sr-only">Mot de passe</label>
          <input
            id="password"
            name="password"
            type={afficherMotDePasse ? 'text' : 'password'}
            autoComplete="current-password"
            required
            placeholder="Mot de passe"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={`${inputClasses} pr-11`}
          />
          <button
            type="button"
            onClick={() => setAfficherMotDePasse((v) => !v)}
            aria-label={afficherMotDePasse ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
            className="tg-tap absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
          >
            {afficherMotDePasse ? (
              <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
                <path d="M3 3l18 18" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                <path
                  d="M10.6 5.2A10.6 10.6 0 0 1 12 5c5 0 9 4 10 7-.5 1.5-1.6 3.2-3.1 4.6M6.7 6.7C4.7 8 3.3 9.9 2 12c1 3 5 7 10 7 1.3 0 2.6-.3 3.7-.7"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path d="M9.9 10a3 3 0 0 0 4.1 4.1" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
                <path
                  d="M2 12c1-3 5-7 10-7s9 4 10 7c-1 3-5 7-10 7s-9-4-10-7Z"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinejoin="round"
                />
                <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.6" />
              </svg>
            )}
          </button>
        </div>
        <SubmitButton loading={loading}>Se connecter</SubmitButton>
      </form>
      <Link
        to="/mot-de-passe-oublie"
        viewTransition
        onClick={() => marquerDirection('/login', '/mot-de-passe-oublie')}
        className="tg-tap mt-4 block w-full text-center text-sm font-medium text-info hover:underline"
      >
        Mot de passe oublié ?
      </Link>
    </AuthLayout>
  )
}
