/**
 * Profondeur de chaque écran dans le parcours utilisateur, pour savoir si une
 * navigation "avance" (glissement depuis la droite, comme Telegram qui ouvre
 * un nouvel écran) ou "recule" (glissement depuis la gauche).
 */
const NIVEAUX_ECRAN = {
  '/': 0,
  '/setup': 1,
  '/login': 1,
  '/mot-de-passe-oublie': 2,
  '/bienvenue': 2,
  '/dashboard': 2,
  '/liste-action': 3,
  '/quoi-commander': 3,
  '/resume-commandes': 3,
  '/stock': 3,
  '/import': 3,
  '/reglages': 3,
  '/aide': 3,
}

function niveauDe(pathname) {
  return NIVEAUX_ECRAN[pathname] ?? 0
}

/**
 * À appeler juste avant navigate()/Link pour poser la direction sur <html>,
 * lue ensuite par les animations CSS de transition de page (index.css).
 */
export function marquerDirection(pathnameActuel, pathnameCible) {
  const direction = niveauDe(pathnameCible) < niveauDe(pathnameActuel) ? 'arriere' : 'avant'
  document.documentElement.dataset.navDirection = direction
}
