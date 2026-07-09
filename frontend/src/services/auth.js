import api, { getToken, getStoredEmail, getStoredOfficineNom, storeSession, clearSession } from './api'

export const isAuthenticated = () => Boolean(getToken())
export const getUserEmail = getStoredEmail
export const getOfficineNom = getStoredOfficineNom

export function getErrorMessage(error, fallback = 'Une erreur est survenue. Réessayez.') {
  if (!error.response) {
    if (error.code === 'ECONNABORTED') {
      return 'Le traitement prend plus de temps que prévu (fichier volumineux ?). Réessayez.'
    }
    return 'Impossible de contacter le serveur. Vérifiez votre connexion.'
  }
  const detail = error.response.data?.detail
  return typeof detail === 'string' ? detail : fallback
}

export async function checkIsSetup() {
  const { data } = await api.get('/auth/is-setup')
  return data
}

export async function setup({ email, password, officineNom }) {
  const { data } = await api.post('/auth/setup', {
    email,
    password,
    officine: { nom: officineNom },
  })
  storeSession(data.access_token, email, data.officine_nom)
  return data
}

export async function login({ email, password }) {
  const { data } = await api.post('/auth/login', { email, password })
  storeSession(data.access_token, email, data.officine_nom)
  return data
}

export async function logout() {
  try {
    await api.post('/auth/logout')
  } finally {
    clearSession()
  }
}

export async function changePassword({ currentPassword, newPassword }) {
  const { data } = await api.patch('/auth/me/password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
  return data
}

export async function requestPasswordReset(email) {
  const { data } = await api.post('/auth/forgot-password', { email })
  return data
}

export async function resetPassword({ email, code, newPassword }) {
  const { data } = await api.post('/auth/reset-password', {
    email,
    code,
    new_password: newPassword,
  })
  return data
}
