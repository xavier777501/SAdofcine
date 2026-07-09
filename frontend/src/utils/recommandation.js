export function formatNb(val) {
  return new Intl.NumberFormat('fr-FR').format(Math.round(val ?? 0))
}

/**
 * Un statut urgent (RUPTURE/CRITIQUE/COMMANDER) avec une quantité à commander
 * nulle ne peut venir que de la neutralisation US-D8 (produit Non-moving et
 * non-Vital) : le calcul refuse de recommander un réapprovisionnement
 * automatique pour un produit qui tourne trop rarement.
 */
export function estNeutralise(v) {
  return v.statut !== 'OK' && (v.qte_a_commander ?? 0) === 0
}

export const MESSAGE_NEUTRALISE =
  'Rotation trop rare pour un réapprovisionnement automatique — vérifiez ce produit avant de commander.'

/** Texte de recommandation en langage clair, sans jargon (cahier des charges section 9). */
export function texteRecommandation(v) {
  if (estNeutralise(v)) return MESSAGE_NEUTRALISE
  if (v.statut === 'RUPTURE') {
    return `Stock épuisé — vous pouvez commander ${formatNb(v.qte_a_commander)} unités dès que possible.`
  }
  if (v.statut === 'CRITIQUE') {
    return `Stock critique — vous pouvez commander ${formatNb(v.qte_a_commander)} unités rapidement.`
  }
  if (v.statut === 'COMMANDER' && v.qte_a_commander > 0) {
    return `Sur la base de ces ventes, vous pouvez commander ${formatNb(v.qte_a_commander)} unités.`
  }
  return `Votre stock actuel (${formatNb(v.stock_actuel)} unités) couvre encore vos besoins — rien à commander pour l'instant.`
}
