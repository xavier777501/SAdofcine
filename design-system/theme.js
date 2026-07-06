/**
 * Gestion du thème clair/sombre — indépendant de React, réutilisable partout.
 * Stocke le choix dans localStorage et l'applique via l'attribut
 * data-theme sur <html> (voir tokens.css : :root[data-theme='dark']).
 */
const THEME_KEY = 'bootstrap_theme'

function prefersDark() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

export function getTheme() {
  return localStorage.getItem(THEME_KEY) || (prefersDark() ? 'dark' : 'light')
}

function applyTheme(theme) {
  const root = document.documentElement
  root.dataset.theme = theme
  // Toggle aussi la classe .dark pour compatibilité directe avec le
  // `@custom-variant dark (&:where(.dark, .dark *));` de Tailwind v4.
  root.classList.toggle('dark', theme === 'dark')
}

/** À appeler une seule fois, avant le premier rendu, pour éviter le flash. */
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
