import api from './api'

export async function getKpis() {
  const { data } = await api.get('/dashboard/kpis')
  return data
}

export async function getListeAction() {
  const { data } = await api.get('/dashboard/liste-action')
  return data
}

export async function getVentesM1() {
  const { data } = await api.get('/dashboard/ventes-m1')
  return data
}

export async function getANePasCommander() {
  const { data } = await api.get('/dashboard/a-ne-pas-commander')
  return data
}

export async function getCommandePlafonnee() {
  const { data } = await api.get('/dashboard/commande-plafonnee')
  return data
}

export async function exportListe(format) {
  const { data } = await api.get('/dashboard/export', {
    params: { format },
    responseType: 'blob',
  })
  const url = URL.createObjectURL(data)
  const a = document.createElement('a')
  a.href = url
  a.download = `sad_officine_liste_action.${format}`
  a.click()
  URL.revokeObjectURL(url)
}
