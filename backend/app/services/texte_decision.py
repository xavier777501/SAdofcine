"""
US-E3 — Génération du texte de décision en langage clair pour le pharmacien.
Aucun jargon logistique visible : pas de CMM, EOQ, σ, Z, FSN, VED dans les textes.
"""
from __future__ import annotations
from typing import Optional


# Matrice statut × VED → texte principal
_TEXTES: dict[tuple[str, Optional[str]], str] = {
    ("RUPTURE",  "Vital"):     "Médicament vital épuisé — commander en urgence absolue.",
    ("RUPTURE",  "Essentiel"): "Produit essentiel en rupture — réapprovisionner immédiatement.",
    ("RUPTURE",  "Désirable"): "Rupture de stock — commander dès que possible.",
    ("RUPTURE",  None):        "Rupture de stock — commander dès que possible.",

    ("CRITIQUE", "Vital"):     "Réserve vitale presque épuisée — anticiper la commande sans délai.",
    ("CRITIQUE", "Essentiel"): "Stock essentiel sous le seuil critique — commander rapidement.",
    ("CRITIQUE", "Désirable"): "Stock sous le seuil d'alerte — prévoir une commande prochaine.",
    ("CRITIQUE", None):        "Stock sous le seuil d'alerte — prévoir une commande prochaine.",

    ("COMMANDER", "Vital"):    "Produit vital à réapprovisionner — inclure dans la prochaine commande.",
    ("COMMANDER", "Essentiel"):"Produit essentiel à commander lors du prochain cycle.",
    ("COMMANDER", "Désirable"):"Stock sous le point de commande — à inclure dans la prochaine commande.",
    ("COMMANDER", None):       "Stock sous le point de commande — à inclure dans la prochaine commande.",
}

_SUFFIXE_FSN = {
    "Slow":        " (produit à rotation lente)",
    "Non-moving":  " (produit non-mouvant — vérifier l'utilité avant de commander)",
}


def generer_texte(statut: str, ved: Optional[str], fsn: Optional[str]) -> str:
    """
    Génère un texte de décision lisible par un pharmacien non technique.
    Combine statut + VED (niveau de risque) + FSN (rotation) sans jargon.
    """
    texte = _TEXTES.get((statut, ved)) or _TEXTES.get((statut, None), "")
    suffixe = _SUFFIXE_FSN.get(fsn or "", "")
    return texte + suffixe
