"""
Liste de démarrage VED — section 6.6 du cahier des charges V7.

L'application embarque une liste de molécules reconnues comme vitales
(urgences et médicaments essentiels courants) et les pré-coche VED = Vital
par correspondance automatique sur la désignation, au premier import
historique. Objectif explicite du cahier des charges : rendre la ligne de
sécurité "CRITIQUE + Vital" (section 6.7) fonctionnelle dès le premier jour,
même pour un pharmacien qui ne renseigne jamais le VED manuellement. Liste de
départ non exhaustive, ajustable ensuite par le pharmacien.
"""
from __future__ import annotations

import re
import unicodedata

# Mots-clés dérivés de la liste de départ du cahier des charges (section 6.6).
# Les variantes de dosage/forme ("injectable", "auto-injectable", "poudre
# injectable (méningite)", "rectal (enfant)"...) sont volontairement omises :
# elles ne changent rien à la molécule et empêcheraient la correspondance
# partielle attendue par le cahier des charges.
LISTE_DEMARRAGE_VED = [
    "Adrénaline",
    "Insuline",
    "Oxytocine",
    "Sulfate de magnésium",
    "Artésunate",
    "Quinine",
    "Diazépam",
    "Atropine",
    "Furosémide",
    "Hydrocortisone",
    "Dopamine",
    "Dobutamine",
    "Naloxone",
    "Héparine",
    "Enoxaparine",
    "Vitamine K1",
    "Gluconate de calcium",
    "Chlorure de potassium",
    "Sérum glucosé",
    "Sérum salé",
    "Ringer lactate",
    "Amoxicilline",
    "Ceftriaxone",
    "Ampicilline",
    "Gentamicine",
    "Métronidazole",
    "Misoprostol",
    "Ergométrine",
    "Réhydratation orale",
    "SRO",
    "Salbutamol",
    "Morphine",
    "Tramadol",
    "Phénobarbital",
    "Anti-venin",
    "Immunoglobuline antitétanique",
    "Vaccin antitétanique",
    "Artéméther",
    "Doxycycline",
    "Ciprofloxacine",
    "Amikacine",
]


def _normaliser(texte: str) -> str:
    """Minuscules, sans accents, pour une comparaison tolérante."""
    sans_accents = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode("ascii")
    return sans_accents.lower()


def _mot_clefs_normalises() -> list[str]:
    return [_normaliser(m) for m in LISTE_DEMARRAGE_VED]


_MOTS_CLEFS_NORMALISES = _mot_clefs_normalises()


def correspond_liste_demarrage(designation: str | None) -> bool:
    """
    True si la désignation correspond (même partiellement) à une molécule de
    la liste de démarrage VED, en tolérant accents/casse/variantes de
    dosage/forme. Les mots-clés courts (ex. "SRO") sont bornés par des
    limites de mot pour éviter les faux positifs sur une sous-chaîne.
    """
    if not designation:
        return False
    normalisee = _normaliser(designation)
    for mot_clef in _MOTS_CLEFS_NORMALISES:
        if len(mot_clef) <= 4:
            if re.search(rf"\b{re.escape(mot_clef)}\b", normalisee):
                return True
        elif mot_clef in normalisee:
            return True
    return False
