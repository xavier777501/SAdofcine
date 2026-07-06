import api from './api'

export async function lancerCalcul() {
  const { data } = await api.post('/calcul/lancer')
  return data
}
