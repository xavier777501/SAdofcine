import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="min-h-screen bg-surface dark:bg-slate-900 flex flex-col items-center justify-center text-center px-4">
      <h1 className="text-4xl font-bold text-slate-900 dark:text-slate-100">404</h1>
      <p className="mt-2 text-slate-500 dark:text-slate-400">Cette page n'existe pas.</p>
      <Link to="/" viewTransition className="tg-tap mt-6 text-brand font-medium hover:underline">
        Retour à l'accueil
      </Link>
    </div>
  )
}
