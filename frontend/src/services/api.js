import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const TOKEN_KEY = 'stockaid_token'
const EMAIL_KEY = 'stockaid_email'
const OFFICINE_NOM_KEY = 'stockaid_officine_nom'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function getStoredEmail() {
  return localStorage.getItem(EMAIL_KEY)
}

export function getStoredOfficineNom() {
  return localStorage.getItem(OFFICINE_NOM_KEY)
}

export function storeSession(token, email, officineNom) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(EMAIL_KEY, email)
  if (officineNom) {
    localStorage.setItem(OFFICINE_NOM_KEY, officineNom)
  }
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(EMAIL_KEY)
  localStorage.removeItem(OFFICINE_NOM_KEY)
}

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearSession()
      if (window.location.pathname !== '/login') {
        window.location.assign('/login')
      }
    }
    return Promise.reject(error)
  },
)

export default api
