import api from './api'

export const getReferences = (signal) =>
  api.get('/references', { signal, timeout: 60000 }).then(r => r.data)

export const updateVed = (id, ved) =>
  api.patch(`/references/${id}/ved`, { ved }).then(r => r.data)

export const updateRisque = (id, jours) =>
  api.patch(`/references/${id}/risque-fournisseur`, { risque_fournisseur_jours: jours }).then(r => r.data)
