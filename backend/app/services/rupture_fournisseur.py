"""
Gestion de la rupture fournisseur — section 6.8 du cahier des charges V9.

Le pharmacien peut mettre une référence "en attente fournisseur" jusqu'à une
date de réévaluation, quand son grossiste habituel ne l'a pas non plus en
stock. Pendant ce délai, la référence est reléguée hors de la liste
d'action, du plafond budgétaire et de l'encart d'alerte 7.0 — sauf exception
stricte : une référence RUPTURE + Vital ne doit jamais pouvoir être masquée
de cette façon, même temporairement.
"""
from __future__ import annotations

from datetime import date

from app.models.reference import Reference


def en_attente_fournisseur(ref: Reference, aujourdhui: date | None = None) -> bool:
    """True si la référence est actuellement mise en attente fournisseur
    (date de réévaluation non dépassée). Une date passée redevient inactive
    automatiquement, sans qu'aucun job ne doive nettoyer le champ."""
    if ref.fournisseur_indisponible_jusqu_au is None:
        return False
    aujourdhui = aujourdhui or date.today()
    return ref.fournisseur_indisponible_jusqu_au >= aujourdhui


def doit_etre_masquee(ref: Reference, aujourdhui: date | None = None) -> bool:
    """
    True si la référence doit être exclue de la liste d'action, du plafond
    et de l'encart 7.0 à cause d'une mise en attente fournisseur en cours.
    Exception absolue (section 6.8) : une référence RUPTURE + Vital reste
    toujours visible, quelle que soit la mise en attente. Une inclusion
    manuelle explicite (section 6.7 : "le pharmacien garde toujours la
    main") bypasse aussi la mise en attente, pour la même raison qu'elle
    bypasse déjà le plafond budgétaire.
    """
    if not en_attente_fournisseur(ref, aujourdhui):
        return False
    if ref.inclusion_manuelle == "inclure":
        return False
    return not (ref.statut == "RUPTURE" and ref.ved == "Vital")
