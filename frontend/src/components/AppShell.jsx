import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { getOfficineNom, logout } from '../services/auth'
import { marquerDirection } from '../services/pageTransition'
import Logo from './Logo'
import ThemeToggle from './ThemeToggle'

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
]

export default function AppShell({ children }) {
  const location = useLocation()
  const navigate = useNavigate()

  function handleNavClick(to) {
    marquerDirection(location.pathname, to)
  }

  async function handleLogout() {
    try {
      await logout()
    } finally {
      marquerDirection(location.pathname, '/login')
      navigate('/login', { replace: true, viewTransition: true })
    }
  }

  return (
    <div className="flex min-h-screen bg-surface dark:bg-slate-900">
      <aside className="w-60 shrink-0 hidden md:flex flex-col bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700">
        <div className="px-5 py-6 flex flex-col items-center gap-2 text-center">
          <Logo className="h-10 w-10 rounded-xl" />
          <span className="brand-name text-xl leading-none text-slate-900 dark:text-slate-100">StockAid</span>
        </div>

        <nav className="flex-1 px-3 mt-2 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              viewTransition
              onClick={() => handleNavClick(item.to)}
              className={({ isActive }) =>
                `tg-tap flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors hover:font-semibold ${
                  isActive
                    ? 'bg-brand-light dark:bg-brand/10 text-brand-dark dark:text-brand'
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
                }`
              }
            >
              {item.icon}
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="px-3 py-4 border-t border-slate-200 dark:border-slate-700 space-y-3">
          <div className="flex items-center justify-between px-1">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300 truncate">{getOfficineNom()}</p>
            <ThemeToggle />
          </div>
          <button
            onClick={handleLogout}
            className="tg-tap w-full rounded-lg border border-info text-info px-3 py-2 text-sm font-medium transition-all hover:bg-info-light dark:hover:bg-info/10"
          >
            Se déconnecter
          </button>
        </div>
      </aside>

      <main className="flex-1 min-w-0 overflow-y-auto">{children}</main>
    </div>
  )
}
