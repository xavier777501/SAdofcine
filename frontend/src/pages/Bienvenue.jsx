import { useNavigate } from 'react-router-dom'
import Logo from '../components/Logo'
import ThemeToggle from '../components/ThemeToggle'
import { getOfficineNom } from '../services/auth'
import { marquerDirection } from '../services/pageTransition'

function salutationDuMoment() {
  const heure = new Date().getHours()
  if (heure >= 5 && heure < 18) return 'Bonjour'
  return 'Bonsoir'
}

export default function Bienvenue() {
  const navigate = useNavigate()

  function handleContinuer() {
    marquerDirection('/bienvenue', '/dashboard')
    navigate('/dashboard', { replace: true, viewTransition: true })
  }

  return (
    <div className="min-h-screen relative bg-surface dark:bg-slate-900 flex flex-col items-center justify-center px-4 py-10">
      <ThemeToggle className="absolute top-4 right-4" />
      <div className="w-full max-w-md text-center">
        <Logo className="h-14 w-14 mx-auto mb-3 rounded-xl shadow-md" />
        <p className="brand-name text-5xl leading-none text-slate-900 dark:text-slate-100">StockAid</p>

        <h1 className="mt-8 text-2xl font-bold text-slate-900 dark:text-slate-100">
          {salutationDuMoment()}, {getOfficineNom()} !
        </h1>
        <p className="mt-3 text-slate-500 dark:text-slate-400">
          Gérez votre stock, <span className="text-brand font-semibold">sans y penser.</span>
        </p>

        <button
          onClick={handleContinuer}
          className="tg-tap mt-10 w-full rounded-lg bg-brand-gradient px-4 py-3 font-semibold text-white shadow-sm transition-all hover:shadow-brand hover:-translate-y-0.5"
        >
          Accéder au tableau de bord
        </button>
      </div>
    </div>
  )
}
