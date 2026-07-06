import { useRef, useState } from 'react'
import { getTheme, setTheme } from '../theme'

const TRANSITION_DURATION_MS = 550

/**
 * Bouton soleil/lune avec transition circulaire (View Transitions API) qui
 * révèle le nouveau thème depuis le point cliqué. Dégrade proprement vers un
 * changement instantané si l'API n'est pas supportée ou si l'utilisateur a
 * demandé de réduire les animations.
 */
export default function ThemeToggle({ className = '' }) {
  const [theme, setThemeState] = useState(getTheme)
  const buttonRef = useRef(null)

  async function handleClick() {
    const next = theme === 'dark' ? 'light' : 'dark'

    if (!document.startViewTransition || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setTheme(next)
      setThemeState(next)
      return
    }

    const rect = buttonRef.current.getBoundingClientRect()
    const x = rect.left + rect.width / 2
    const y = rect.top + rect.height / 2
    const endRadius = Math.hypot(
      Math.max(x, window.innerWidth - x),
      Math.max(y, window.innerHeight - y),
    )

    document.documentElement.dataset.vt = 'theme'
    const transition = document.startViewTransition(() => {
      setTheme(next)
      setThemeState(next)
    })

    try {
      await transition.ready
      document.documentElement.animate(
        { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${endRadius}px at ${x}px ${y}px)`] },
        { duration: TRANSITION_DURATION_MS, easing: 'ease-in-out', pseudoElement: '::view-transition-new(root)' },
      )
    } catch {
      // API non supportée : le thème a déjà changé, juste sans animation
    } finally {
      transition.finished.finally(() => {
        delete document.documentElement.dataset.vt
      })
    }
  }

  const isDark = theme === 'dark'

  return (
    <button
      ref={buttonRef}
      type="button"
      onClick={handleClick}
      aria-label={isDark ? 'Activer le mode clair' : 'Activer le mode sombre'}
      title={isDark ? 'Mode clair' : 'Mode sombre'}
      className={`tg-tap inline-flex items-center justify-center h-9 w-9 rounded-[var(--radius-md)] border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition ${className}`}
    >
      {isDark ? (
        <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
          <circle cx="12" cy="12" r="4.5" fill="currentColor" />
          <g stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
            <path d="M12 2.5v2.2" />
            <path d="M12 19.3v2.2" />
            <path d="M4.2 4.2l1.55 1.55" />
            <path d="M18.25 18.25l1.55 1.55" />
            <path d="M2.5 12h2.2" />
            <path d="M19.3 12h2.2" />
            <path d="M4.2 19.8l1.55-1.55" />
            <path d="M18.25 5.75l1.55-1.55" />
          </g>
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5" aria-hidden="true">
          <path d="M20.7 14.9c-.2-.3-.6-.4-.9-.3-1 .4-2.1.6-3.2.5-3.8-.3-6.9-3.4-7.2-7.2-.1-1.1.1-2.2.5-3.2.1-.3 0-.7-.3-.9-.3-.2-.7-.2-.9 0C5.1 5.4 3.5 8.5 3.8 11.9c.4 4.7 4.2 8.5 8.9 8.9 3.4.3 6.5-1.3 8.1-3.9.2-.3.2-.7-.1-1z" />
        </svg>
      )}
    </button>
  )
}
