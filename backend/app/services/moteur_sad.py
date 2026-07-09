"""
Moteur de calcul SAD OFFICINE.

Toutes les fonctions sont pures (pas d'accès BDD). Elles prennent des valeurs
scalaires ou des listes et retournent des résultats numériques/textuels.

Source de vérité : SAD_OFFICINE_REFERENCE_DEVELOPPEUR.xlsx, onglet MODÈLE SAD.
"""
from __future__ import annotations

import math
import statistics
from typing import Optional

from scipy.stats import norm


# ─────────────────────────────────────────────────────────────────────────────
# VED → niveau de service visé, et facteur Z = INV.NORMALE.STANDARD(niveau)
# ─────────────────────────────────────────────────────────────────────────────

NIVEAU_SERVICE_PAR_DEFAUT: dict[str | None, float] = {
    "Vital":     0.99,
    "Essentiel": 0.95,
    "Désirable": 0.90,
    None:        0.95,   # Non renseigné → 95 % par défaut
}


def get_z(ved: str | None, niveaux_service: Optional[dict] = None) -> float:
    """
    Facteur de service Z = INV.NORMALE.STANDARD(niveau de service visé selon VED).

    Le niveau de service par statut VED est configurable par l'officine
    (section 6.6 du cahier des charges) : si `niveaux_service` est fourni
    (dict VED → % entre 0 et 1, tel que stocké sur ParametreOfficine), il est
    utilisé ; sinon les valeurs par défaut du cahier des charges s'appliquent.
    Modifier le % recalcule donc automatiquement Z, et par ricochet tout le
    moteur (SS, PC, S, quantités).
    """
    niveaux = niveaux_service or NIVEAU_SERVICE_PAR_DEFAUT
    niveau_service = niveaux.get(ved, niveaux.get(None, 0.95))
    return float(norm.ppf(niveau_service))


# ─────────────────────────────────────────────────────────────────────────────
# US-D1 : CMM et CMMax
# ─────────────────────────────────────────────────────────────────────────────

def calc_cmm(ventes: list[float]) -> float:
    """
    Consommation Mensuelle Moyenne = somme des 12 mois / 12.
    Les valeurs négatives ont déjà été mises à 0 à l'import.
    """
    if not ventes:
        return 0.0
    return sum(max(0.0, v) for v in ventes) / 12.0


def calc_cmmax(ventes: list[float]) -> float:
    """Pic de consommation sur 12 mois."""
    if not ventes:
        return 0.0
    return max(max(0.0, v) for v in ventes)


# ─────────────────────────────────────────────────────────────────────────────
# US-D3 : Écart-type mensuel σ
# ─────────────────────────────────────────────────────────────────────────────

def calc_sigma(ventes: list[float]) -> float:
    """
    Écart-type des ventes mensuelles sur 12 mois (écart-type population, N).
    Remplace l'ancien proxy CMMax - CMM (V2 juin 2026).
    Retourne 0 si moins de 2 mois de données.
    """
    vals = [max(0.0, v) for v in ventes]
    if len(vals) < 2:
        return 0.0
    # Population stdev (comme Excel ECARTYPE.PEARSON / stdev sur N)
    mean = sum(vals) / len(vals)
    variance = sum((v - mean) ** 2 for v in vals) / len(vals)
    return math.sqrt(variance)


# ─────────────────────────────────────────────────────────────────────────────
# US-D7 : Classification FSN
# ─────────────────────────────────────────────────────────────────────────────

def calc_fsn(ventes: list[float]) -> str:
    """
    Fast / Slow / Non-moving selon le nombre de mois avec vente > 0.
      Fast       : >= 10 mois
      Slow       : 3 à 9 mois
      Non-moving : < 3 mois
    """
    mois_actifs = sum(1 for v in ventes if v > 0)
    if mois_actifs >= 10:
        return "Fast"
    if mois_actifs >= 3:
        return "Slow"
    return "Non-moving"


# ─────────────────────────────────────────────────────────────────────────────
# US-D4 : SS continu, PC, statut
# ─────────────────────────────────────────────────────────────────────────────

def calc_ss(z: float, sigma: float, dl_max_jours: int) -> float:
    """
    Stock de sécurité (mode continu) :
    SS = MAX(0, Z × σ × RACINE(DLmax / 30))
    """
    if dl_max_jours <= 0 or sigma <= 0:
        return 0.0
    return max(0.0, z * sigma * math.sqrt(dl_max_jours / 30.0))


def calc_pc(cmm: float, dl_moy_jours: int, ss: float) -> float:
    """
    Point de commande (mode continu) :
    PC = (CMM / 30 × DLmoy) + SS
    """
    return (cmm / 30.0) * dl_moy_jours + ss


def calc_statut(stock: float, ss: float, pc: float) -> str:
    """
    Statut d'approvisionnement :
      RUPTURE  : stock <= 0
      CRITIQUE : stock <= SS
      COMMANDER: stock <= PC
      OK       : sinon
    """
    if stock <= 0:
        return "RUPTURE"
    if stock <= ss:
        return "CRITIQUE"
    if stock <= pc:
        return "COMMANDER"
    return "OK"


# ─────────────────────────────────────────────────────────────────────────────
# US-D5 : EOQ (Wilson) — indicatif uniquement
# ─────────────────────────────────────────────────────────────────────────────

def calc_eoq(
    cmm: float,
    cout_commande: float,
    taux_detention: float,
    prix_cession: Optional[float],
) -> Optional[float]:
    """
    Quantité économique de commande (Wilson) :
    EOQ = RACINE(2 × Demande_annuelle × Coût_commande / (Taux_détention × Prix_cession))

    Retourne None si les données sont insuffisantes.
    Indicatif uniquement — ne pilote jamais la quantité commandée.
    """
    if not prix_cession or prix_cession <= 0 or taux_detention <= 0 or cmm <= 0:
        return None
    demande_annuelle = cmm * 12
    denominateur = taux_detention * prix_cession
    if denominateur <= 0:
        return None
    return math.sqrt(2 * demande_annuelle * cout_commande / denominateur)


# ─────────────────────────────────────────────────────────────────────────────
# US-D6 : Cycle périodique (SS, S, quantité à commander)
# ─────────────────────────────────────────────────────────────────────────────

def calc_ss_periodique(
    z: float,
    sigma: float,
    dl_max_jours: int,
    T: int,
    Y: int,
) -> float:
    """
    Stock de sécurité (mode périodique) :
    SS_periodique = MAX(0, Z × σ × RACINE((DLmax + T + Y) / 30))
    """
    total_jours = dl_max_jours + T + Y
    if total_jours <= 0 or sigma <= 0:
        return 0.0
    return max(0.0, z * sigma * math.sqrt(total_jours / 30.0))


def calc_niveau_recompletement(
    cmm: float,
    dl_moy_jours: int,
    T: int,
    Y: int,
    ss_periodique: float,
) -> float:
    """
    Niveau de recomplètement S :
    S = (CMM / 30 × (DLmoy + T + Y)) + SS_periodique
    """
    return (cmm / 30.0) * (dl_moy_jours + T + Y) + ss_periodique


def calc_qte_commander(S: float, stock: float) -> float:
    """
    Quantité à commander (cycle périodique) :
    Qté = MAX(0, ROUND(S - stock_actuel, 0))
    Arrondi Excel (0.5 → vers le haut), pas l'arrondi bancaire de Python.
    """
    diff = S - stock
    if diff <= 0:
        return 0.0
    return float(math.floor(diff + 0.5))


def calc_qte_commander_continu(pc: float, stock: float, cmm: float) -> float:
    """
    Quantité à commander (mode continu) :
    Commande la différence jusqu'au niveau de recomplètement simplifié = PC + CMM.
    """
    if stock >= pc:
        return 0.0
    return max(0.0, round(pc + cmm - stock, 0))


# ─────────────────────────────────────────────────────────────────────────────
# US-D8 : Neutralisation des Non-moving
# ─────────────────────────────────────────────────────────────────────────────

def appliquer_neutralisation_fsn(
    fsn: str,
    ved: Optional[str],
    qte_periodique: float,
    qte_continu: float,
) -> tuple[float, float]:
    """
    Si Non-moving :
      - qté = 0, sauf si VED = Vital → qté = 1
    Retourne (qte_periodique, qte_continu) après neutralisation.
    """
    if fsn != "Non-moving":
        return qte_periodique, qte_continu
    if ved == "Vital":
        return 1.0, 1.0
    return 0.0, 0.0


# ─────────────────────────────────────────────────────────────────────────────
# US-D2 : Classification ABC
# ─────────────────────────────────────────────────────────────────────────────

def calc_classes_abc(
    references: list[dict],
) -> dict[str, str]:
    """
    Classifie toutes les références A/B/C selon leur poids dans le CA annuel cumulé.

    Entrée  : liste de dicts {"id": ..., "cmm": float, "prix_public": float | None}
    Sortie  : dict {id → "A" | "B" | "C"}

    - Tri décroissant par CA annuel (CMM × 12 × Prix public, section 6.2)
    - A : jusqu'à 80 % du CA cumulé
    - B : de 80 % à 95 %
    - C : au-delà
    """
    # Calcul CA pour chaque référence
    avec_ca = []
    for ref in references:
        cmm = ref.get("cmm") or 0.0
        prix = ref.get("prix_public") or 0.0
        ca = cmm * 12 * prix
        avec_ca.append({"id": ref["id"], "ca": ca, "cmm": cmm})

    total_ca = sum(r["ca"] for r in avec_ca)
    if total_ca <= 0:
        # Pas de prix : fallback ABC par volume CMM annuel
        total_cmm = sum(r["cmm"] for r in avec_ca)
        if total_cmm <= 0:
            return {r["id"]: "C" for r in avec_ca}
        avec_ca.sort(key=lambda r: r["cmm"], reverse=True)
        classes: dict[str, str] = {}
        cumul = 0.0
        for item in avec_ca:
            ratio_avant = cumul / total_cmm
            cumul += item["cmm"]
            if ratio_avant < 0.80:
                classes[item["id"]] = "A"
            elif ratio_avant < 0.95:
                classes[item["id"]] = "B"
            else:
                classes[item["id"]] = "C"
        return classes

    avec_ca.sort(key=lambda r: r["ca"], reverse=True)

    classes: dict[str, str] = {}
    cumul = 0.0
    for item in avec_ca:
        # Classifier selon le cumul AVANT ajout de cet article
        ratio_avant = cumul / total_ca
        cumul += item["ca"]
        if ratio_avant < 0.80:
            classes[item["id"]] = "A"
        elif ratio_avant < 0.95:
            classes[item["id"]] = "B"
        else:
            classes[item["id"]] = "C"

    return classes


# ─────────────────────────────────────────────────────────────────────────────
# Indicateurs supplémentaires
# ─────────────────────────────────────────────────────────────────────────────

def calc_couverture_jours(stock: float, cmm: float) -> Optional[float]:
    """Nombre de jours de stock restant au rythme de la CMM."""
    if cmm <= 0:
        return None
    return (stock / cmm) * 30.0


def calc_tresorerie_liberee(
    stock: float,
    niveau_recompletement: float,
    prix_cession: Optional[float],
) -> float:
    """
    Trésorerie immobilisée en excès = MAX(0, stock - S) × prix_cession.
    Représente le cash qui pourrait être libéré si le stock était ramené à S.
    """
    if not prix_cession or prix_cession <= 0:
        return 0.0
    exces = max(0.0, stock - niveau_recompletement)
    return exces * prix_cession
