import { useState } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { getOfficineNom, logout } from '../services/auth'
import { marquerDirection } from '../services/pageTransition'
import Logo from './Logo'
import ThemeToggle from './ThemeToggle'
import ConfirmDialog from './ConfirmDialog'

const NAV_ITEMS = [
  {
    to: '/dashboard',
    label: 'Tableau de bord',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
        <path
          d="M4 13h6V4H4v9Zm0 7h6v-5H4v5Zm10 0h6V11h-6v9Zm0-16v5h6V4h-6Z"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
  {
    to: '/liste-action',
    label: "Liste d'action",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
        <path
          d="M9 4.5h6a1 1 0 0 1 1 1V6h1.5A1.5 1.5 0 0 1 19 7.5v11A1.5 1.5 0 0 1 17.5 20h-11A1.5 1.5 0 0 1 5 18.5v-11A1.5 1.5 0 0 1 6.5 6H8v-.5a1 1 0 0 1 1-1Z"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinejoin="round"
        />
        <path d="M9 11.5l1.5 1.5L14 9.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M9 16h6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    to: '/quoi-commander',
    label: 'Quoi commander',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
        <path d="M12 21c4.5-3 7.5-6.5 7.5-10.5A7.5 7.5 0 0 0 4.5 10.5C4.5 14.5 7.5 18 12 21Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
        <path d="M9.5 11.5 11 13l3.5-4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    to: '/resume-commandes',
    label: 'Résumé des commandes',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
        <path
          d="M7 4.5h7l4 4V19a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V5.5a1 1 0 0 1 1-1Z"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinejoin="round"
        />
        <path d="M14 4.5V9h4" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
        <path d="M9 13h6M9 16h4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    to: '/stock',
    label: 'Stock',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
        <path
          d="M20 7H4a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1V8a1 1 0 0 0-1-1ZM3 7l4-4h10l4 4"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path d="M9 12h6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
      </svg>
    ),
  },
  {
    to: '/import',
    label: 'Importer',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
        <path
          d="M12 15V4m0 0 4 4m-4-4-4 4M5 15v3a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-3"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
  {
    to: '/reglages',
    label: 'Réglages',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
        <path
          d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"
          stroke="currentColor"
          strokeWidth="1.6"
        />
        <path
          d="m19.4 13.5-.8-.46a1 1 0 0 1-.5-.87v-.34a1 1 0 0 1 .5-.87l.8-.46a1 1 0 0 0 .37-1.36l-1-1.74a1 1 0 0 0-1.36-.37l-.8.46a1 1 0 0 1-1 0 6.8 6.8 0 0 0-.3-.17 1 1 0 0 1-.5-.87v-.92a1 1 0 0 0-1-1h-2a1 1 0 0 0-1 1v.92a1 1 0 0 1-.5.87q-.15.08-.3.17a1 1 0 0 1-1 0l-.8-.46a1 1 0 0 0-1.36.37l-1 1.74a1 1 0 0 0 .37 1.36l.8.46a1 1 0 0 1 .5.87v.34a1 1 0 0 1-.5.87l-.8.46a1 1 0 0 0-.37 1.36l1 1.74a1 1 0 0 0 1.36.37l.8-.46a1 1 0 0 1 1 0q.15.09.3.17a1 1 0 0 1 .5.87v.92a1 1 0 0 0 1 1h2a1 1 0 0 0 1-1v-.92a1 1 0 0 1 .5-.87q.15-.08.3-.17a1 1 0 0 1 1 0l.8.46a1 1 0 0 0 1.36-.37l1-1.74a1 1 0 0 0-.37-1.36Z"
          stroke="currentColor"
          strokeWidth="1.4"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
  {
    to: '/aide',
    label: 'Aide',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
        <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="1.6" />
        <path
          d="M9.8 9.5a2.2 2.2 0 1 1 3.3 1.9c-.7.45-1.1.85-1.1 1.6v.3"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="12" cy="16.3" r="0.9" fill="currentColor" />
      </svg>
    ),
  },
]

function initiales(nom) {
  if (!nom) return '?'
  const mots = nom.trim().split(/\s+/)
  return mots.slice(0, 2).map((m) => m[0]).join('').toUpperCase()
}

export default function AppShell({ children }) {
  const location = useLocation()
  const navigate = useNavigate()
  const [confirmationOuverte, setConfirmationOuverte] = useState(false)

  function handleNavClick(to) {
    marquerDirection(location.pathname, to)
  }

  async function handleLogout() {
    setConfirmationOuverte(false)
    try {
      await logout()
    } finally {
      marquerDirection(location.pathname, '/login')
      navigate('/login', { replace: true, viewTransition: true })
    }
  }

  return (
    <div className="flex min-h-screen bg-surface dark:bg-slate-900">
      <aside className="w-60 shrink-0 hidden md:flex flex-col bg-gradient-to-b from-slate-900 to-slate-950">
        <div className="px-5 py-6 flex flex-col items-center gap-1.5 text-center">
          <Logo className="h-10 w-10 rounded-xl" />
          <span className="brand-name text-xl leading-none text-white">StockAid</span>
          <span className="text-[11px] text-slate-400">Gestion de stock pharmacie</span>
        </div>

        <nav className="flex-1 px-3 mt-2 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              viewTransition
              onClick={() => handleNavClick(item.to)}
              className={({ isActive }) =>
                `tg-tap flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-brand text-white shadow-sm'
                    : 'text-slate-300 hover:bg-white/5 hover:text-white'
                }`
              }
            >
              {item.icon}
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="px-3 py-4 border-t border-slate-800 space-y-3">
          <div className="flex items-center gap-2.5 px-1">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand/20 text-brand text-xs font-bold uppercase">
              {initiales(getOfficineNom())}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-white truncate">{getOfficineNom()}</p>
              <p className="text-[11px] text-slate-400">Pharmacien</p>
            </div>
            <ThemeToggle dark />
          </div>
          <button
            onClick={() => setConfirmationOuverte(true)}
            className="tg-tap w-full flex items-center justify-center gap-2 rounded-lg border border-slate-700 text-slate-300 px-3 py-2 text-sm font-medium transition-all hover:bg-white/5 hover:text-white"
          >
            <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Se déconnecter
          </button>
        </div>
      </aside>

      <main className="flex-1 min-w-0 overflow-y-auto">{children}</main>

      <ConfirmDialog
        open={confirmationOuverte}
        title="Êtes-vous sûr de vouloir vous déconnecter ?"
        confirmLabel="Oui"
        cancelLabel="Non"
        onConfirm={handleLogout}
        onCancel={() => setConfirmationOuverte(false)}
      />
    </div>
  )
}
