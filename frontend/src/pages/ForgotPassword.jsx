import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import AuthLayout from '../components/AuthLayout'
import ErrorBanner from '../components/ErrorBanner'
import SubmitButton from '../components/SubmitButton'
import { requestPasswordReset, resetPassword, getErrorMessage } from '../services/auth'
import { marquerDirection } from '../services/pageTransition'

const MIN_PASSWORD_LENGTH = 8

const inputClasses =
  'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-4 py-3 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 shadow-xs transition-shadow focus:outline-none focus:border-brand focus:shadow-[0_0_0_4px_var(--color-brand-light)]'

export default function ForgotPassword() {
  const navigate = useNavigate()
  const [etape, setEtape] = useState('email') // 'email' | 'code'
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [renvoiOk, setRenvoiOk] = useState(false)

  async function handleEmailSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await requestPasswordReset(email)
      setEtape('code')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  async function handleResetSubmit(e) {
    e.preventDefault()
    setError('')
    setRenvoiOk(false)

    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`Le mot de passe doit contenir au moins ${MIN_PASSWORD_LENGTH} caractères.`)
      return
    }
    if (password !== confirmation) {
      setError('Les deux mots de passe ne correspondent pas.')
      return
    }

    setLoading(true)
    try {
      await resetPassword({ email, code, newPassword: password })
      marquerDirection('/mot-de-passe-oublie', '/login')
      navigate('/login', { replace: true, viewTransition: true, state: { motDePasseReinitialise: true } })
    } catch (err) {
      setError(getErrorMessage(err, 'Code invalide ou expiré.'))
    } finally {
      setLoading(false)
    }
  }

  async function handleRenvoyer() {
    setError('')
    setRenvoiOk(false)
    try {
      await requestPasswordReset(email)
      setRenvoiOk(true)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  return (
    <AuthLayout title={etape === 'email' ? 'Mot de passe oublié' : 'Entrez votre code'}>
      {etape === 'email' ? (
        <form onSubmit={handleEmailSubmit} className="space-y-3" noValidate>
          <ErrorBanner message={error} />
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Indiquez votre email, nous vous envoyons un code de vérification à 6 chiffres.
          </p>
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
          <SubmitButton loading={loading} loadingLabel="Envoi en cours…">Envoyer le code</SubmitButton>
        </form>
      ) : (
        <form onSubmit={handleResetSubmit} className="space-y-3" noValidate>
          <ErrorBanner message={error} />
          {renvoiOk && !error && (
            <div
              role="status"
              className="rounded-lg bg-brand-light dark:bg-brand/10 border border-brand/30 text-brand-dark dark:text-brand text-sm px-4 py-3 text-left"
            >
              Un nouveau code vient d'être envoyé.
            </div>
          )}
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Un code a été envoyé à <strong>{email}</strong>. Entrez-le ci-dessous avec votre nouveau mot de passe.
          </p>
          <div>
            <label htmlFor="code" className="sr-only">Code de vérification</label>
            <input
              id="code"
              name="code"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              required
              maxLength={6}
              placeholder="Code à 6 chiffres"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              className={`${inputClasses} text-center font-semibold tracking-[0.5em]`}
            />
          </div>
          <div>
            <label htmlFor="password" className="sr-only">Nouveau mot de passe</label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="new-password"
              required
              minLength={MIN_PASSWORD_LENGTH}
              placeholder="Nouveau mot de passe"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={inputClasses}
            />
          </div>
          <div>
            <label htmlFor="confirmation" className="sr-only">Confirmer le mot de passe</label>
            <input
              id="confirmation"
              name="confirmation"
              type="password"
              autoComplete="new-password"
              required
              placeholder="Confirmer le mot de passe"
              value={confirmation}
              onChange={(e) => setConfirmation(e.target.value)}
              className={inputClasses}
            />
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {MIN_PASSWORD_LENGTH} caractères minimum.
          </p>
          <SubmitButton loading={loading} loadingLabel="Réinitialisation…">Réinitialiser le mot de passe</SubmitButton>
          <button
            type="button"
            onClick={handleRenvoyer}
            className="tg-tap block w-full rounded-lg border border-info/40 px-4 py-2.5 text-center text-sm font-semibold text-info transition-colors hover:bg-info-light dark:hover:bg-info/10"
          >
            Renvoyer le code
          </button>
        </form>
      )}
      <Link
        to="/login"
        viewTransition
        onClick={() => marquerDirection('/mot-de-passe-oublie', '/login')}
        className="tg-tap mt-6 block w-full rounded-lg border border-slate-200 dark:border-slate-700 px-4 py-2.5 text-center text-sm font-medium text-slate-500 dark:text-slate-400 transition-colors hover:bg-slate-50 dark:hover:bg-slate-700"
      >
        Retour à la connexion
      </Link>
    </AuthLayout>
  )
}
