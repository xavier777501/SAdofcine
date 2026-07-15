"""
Plafond budgétaire de commande — section 6.7 du cahier des charges.

Le pharmacien peut fixer un montant maximum (FCFA) pour une session de
commande. L'application sélectionne les références par ordre de priorité
décroissante et s'arrête dès que le montant cumulé atteint ce seuil. Les
ruptures sur produits Vitaux sont toujours incluses, hors plafond.
"""
from __future__ import annotations

from typing import Optional

from app.models.reference import Reference

STATUTS_ACTIONNABLES = ("RUPTURE", "CRITIQUE", "COMMANDER")


def _priorite(ref: Reference) -> float:
    """
    Ordre de priorité en 10 niveaux, tel que défini section 6.7 (du plus
    urgent au moins urgent). Les combinaisons non couvertes explicitement par
    le tableau du cahier des charges sont rattachées au niveau le plus proche
    de leur statut, par prudence (voir commentaires ci-dessous).
    """
    statut, ved, classe, fsn = ref.statut, ref.ved, ref.classe, ref.fsn

    if statut == "RUPTURE" and ved == "Vital":
        return 1  # HORS PLAFOND — traité séparément, jamais via cette liste
    if statut == "RUPTURE" and ved == "Essentiel" and classe == "A":
        return 2
    if statut == "CRITIQUE" and ved == "Vital":
        return 3
    if statut == "RUPTURE" and (ved == "Désirable" or classe == "B"):
        return 4
    if statut == "CRITIQUE" and ved == "Essentiel" and classe == "A":
        return 5
    if statut == "COMMANDER" and fsn == "Fast" and classe == "A":
        return 6
    if statut == "COMMANDER" and fsn == "Slow" and classe == "A":
        return 7
    if statut == "CRITIQUE" and classe == "B":
        return 8
    if statut == "COMMANDER" and classe == "B":
        return 9
    if classe == "C":
        return 10  # dernier servi, quel que soit le statut (voir section 6.7)

    # Combinaisons non listées explicitement (ex: RUPTURE non-renseigné,
    # CRITIQUE Désirable...) : rattachées juste après le dernier niveau connu
    # de leur statut, pour rester prudent sans contredire le tableau.
    if statut == "RUPTURE":
        return 4.5
    if statut == "CRITIQUE":
        return 8.5
    if statut == "COMMANDER":
        return 9.5
    return 11


def _valeur_fcfa(ref: Reference) -> float:
    return (ref.qte_a_commander or 0.0) * (ref.prix_cession or 0.0)


def _ligne(ref: Reference, hors_plafond: bool = False) -> dict:
    return {
        "id": str(ref.id),
        "code": ref.code,
        "designation": ref.designation,
        "classe": ref.classe,
        "statut": ref.statut,
        "ved": ref.ved,
        "stock_actuel": ref.stock_actuel or 0.0,
        "qte_a_commander": ref.qte_a_commander or 0.0,
        "valeur_fcfa": round(_valeur_fcfa(ref), 0),
        "hors_plafond": hors_plafond,
    }


def prioriser_et_plafonner(references: list[Reference], plafond: Optional[float]) -> dict:
    """
    Applique la priorisation et le plafond aux références actionnables.
    plafond=None ou <=0 : pas de restriction, tout est renvoyé dans "inclus".
    """
    actionnables = [r for r in references if r.statut in STATUTS_ACTIONNABLES]

    hors_plafond_refs = [r for r in actionnables if r.statut == "RUPTURE" and r.ved == "Vital"]
    reste = [r for r in actionnables if not (r.statut == "RUPTURE" and r.ved == "Vital")]
    reste.sort(key=_priorite)

    hors_plafond = [_ligne(r, hors_plafond=True) for r in hors_plafond_refs]

    inclus: list[dict] = []
    reporte: list[dict] = []
    budget_utilise = 0.0
    budget_atteint = False
    sans_restriction = plafond is None or plafond <= 0

    for r in reste:
        valeur = _valeur_fcfa(r)
        if not budget_atteint and (sans_restriction or budget_utilise + valeur <= plafond):
            inclus.append(_ligne(r))
            budget_utilise += valeur
        else:
            budget_atteint = True
            reporte.append(_ligne(r))

    montant_reporte = sum(l["valeur_fcfa"] for l in reporte)
    rupture_non_vitale_reportee = any(l["statut"] == "RUPTURE" for l in reporte)

    return {
        "plafond": plafond,
        "sans_restriction": sans_restriction,
        "budget_utilise": round(budget_utilise, 0),
        "hors_plafond": hors_plafond,
        "inclus": inclus,
        "reporte": reporte,
        "montant_reporte": round(montant_reporte, 0),
        "rupture_non_vitale_reportee": rupture_non_vitale_reportee,
    }
