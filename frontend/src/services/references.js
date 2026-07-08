import api from './api'

export const getReferences = () => api.get('/references').then(r => r.data)

export const updateVed = (id, ved) =>
  api.patch(`/references/${id}/ved`, { ved }).then(r => r.data)

export const updateRisque = (id, jours) =>
  api.patch(`/references/${id}/risque-fournisseur`, { risque_fournisseur_jours: jours }).then(r => r.data)
