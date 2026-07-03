import api, { getToken, getStoredEmail, storeSession, clearSession } from './api'

export const isAuthenticated = () => Boolean(getToken())
export const getUserEmail = getStoredEmail

export function getErrorMessage(error, fallback = 'Une erreur est survenue. Réessayez.') {
  if (!error.response) {
    return 'Impossible de contacter le serveur. Vérifiez votre connexion.'
  }
  const detail = error.response.data?.detail
  return typeof detail === 'string' ? detail : fallback
}

export async function register({ email, password, officineNom }) {
  const { data } = await api.post('/auth/register', {
    email,
    password,
    officine: { nom: officineNom },
  })
  return data
}

export async function login({ email, password }) {
  const { data } = await api.post('/auth/login', { email, password })
  storeSession(data.access_token, email)
  return data
}

export async function logout() {
  try {
    await api.post('/auth/logout')
  } finally {
    clearSession()
  }
}
