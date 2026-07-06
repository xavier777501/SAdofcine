const THEME_KEY = 'stockaid_theme'

function prefersDark() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

export function getTheme() {
  return localStorage.getItem(THEME_KEY) || (prefersDark() ? 'dark' : 'light')
}

function applyTheme(theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark')
}

/**
 * À appeler une seule fois, le plus tôt possible (avant le premier rendu React),
 * pour éviter un flash du mauvais thème au chargement de la page.
 */
export function initTheme() {
  applyTheme(getTheme())
}

export function setTheme(theme) {
  localStorage.setItem(THEME_KEY, theme)
  applyTheme(theme)
}

export function toggleTheme() {
  const next = getTheme() === 'dark' ? 'light' : 'dark'
  setTheme(next)
  return next
}
