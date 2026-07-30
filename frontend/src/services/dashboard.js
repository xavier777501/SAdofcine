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

export async function getAlertesStrategiques() {
  const { data } = await api.get('/dashboard/alertes-strategiques')
  return data
}

export async function inclureToutAlertesStrategiques() {
  const { data } = await api.post('/dashboard/alertes-strategiques/inclure-tout')
  return data
}

export async function getEnAttenteFournisseur() {
  const { data } = await api.get('/dashboard/en-attente-fournisseur')
  return data
}

export async function getHistoriqueCommandes() {
  const { data } = await api.get('/dashboard/historique-commandes')
  return data
}

/**
 * `filtres.statut`/`filtres.classe`/`filtres.recherche` (tous optionnels) :
 * doivent refléter exactement les onglets/filtres actifs à l'écran au
 * moment du clic, sinon le fichier téléchargé ne correspond pas à ce que
 * le pharmacien regarde (ex. il est sur l'onglet "Rupture" mais reçoit
 * toutes les références).
 */
export async function exportListe(format, { statut, classe, recherche } = {}) {
  const params = { format }
  const suffixeParts = []
  if (statut && statut !== 'TOUS') {
    params.statut = statut
    suffixeParts.push(statut.toLowerCase())
  }
  if (classe && classe !== 'TOUS') {
    params.classe = classe
    suffixeParts.push(`classe${classe.toLowerCase()}`)
  }
  if (recherche && recherche.trim()) {
    params.recherche = recherche.trim()
  }
  const suffixe = suffixeParts.length > 0 ? `_${suffixeParts.join('_')}` : ''
  const { data } = await api.get('/dashboard/export', { params, responseType: 'blob' })
  const url = URL.createObjectURL(data)
  const a = document.createElement('a')
  a.href = url
  a.download = `sad_officine_liste_action${suffixe}.${format}`
  a.click()
  URL.revokeObjectURL(url)
}
