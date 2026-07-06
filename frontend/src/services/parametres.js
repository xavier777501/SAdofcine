import api from './api'

export async function getParametres() {
  const { data } = await api.get('/parametres')
  return data
}

export async function updateParametres(changes) {
  const { data } = await api.patch('/parametres', changes)
  return data
}

export const CYCLE_OPTIONS = [
  { value: 0, label: 'En continu (dès que nécessaire)' },
  { value: 10, label: 'Par décade (tous les 10 jours)' },
  { value: 30, label: 'Mensuel (tous les 30 jours)' },
]
