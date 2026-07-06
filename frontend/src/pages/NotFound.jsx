import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="min-h-screen bg-surface flex flex-col items-center justify-center text-center px-4">
      <h1 className="text-4xl font-bold text-slate-900">404</h1>
      <p className="mt-2 text-slate-500">Cette page n'existe pas.</p>
      <Link to="/" className="mt-6 text-brand font-medium hover:underline">
        Retour à l'accueil
      </Link>
    </div>
  )
}
