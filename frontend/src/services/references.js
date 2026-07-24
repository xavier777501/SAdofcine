import api from './api'

export const getReferences = (signal) =>
  api.get('/references', { signal, timeout: 60000 }).then(r => r.data)

export const updateVed = (id, ved) =>
  api.patch(`/references/${id}/ved`, { ved }).then(r => r.data)

export const updateRisque = (id, jours) =>
  api.patch(`/references/${id}/risque-fournisseur`, { risque_fournisseur_jours: jours }).then(r => r.data)

export const updateAjustementCommande = (id, { qteOverride, inclusionManuelle } = {}) =>
  api.patch(`/references/${id}/ajustement-commande`, {
    qte_a_commander_override: qteOverride ?? null,
    inclusion_manuelle: inclusionManuelle ?? null,
  }).then(r => r.data)

export const updateFournisseurIndisponible = (id, dateReevaluation) =>
  api.patch(`/references/${id}/fournisseur-indisponible`, {
    date_reevaluation: dateReevaluation ?? null,
  }).then(r => r.data)
