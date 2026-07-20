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
    Ordre de priorité en 8 niveaux (+ hors plafond), tel que défini section
    6.7 du cahier des charges V7 (du plus urgent au moins urgent). Logique
    centrée sur la classe ABC et la vitesse de rotation (Fast/Slow) — le VED
    ne joue plus de rôle qu'aux deux tout premiers niveaux (hors plafond, et
    CRITIQUE+Vital qui passe devant peu importe sa classe/rotation).

    Toute combinaison non listée explicitement (ex. RUPTURE/CRITIQUE classe B
    Slow, classe C...) tombe dans "le reste" (niveau 8, section 6.7), qui
    n'est départagé que par la valeur FCFA — géré par le tri secondaire dans
    prioriser_et_plafonner, pas ici.
    """
    statut, ved, classe, fsn = ref.statut, ref.ved, ref.classe, ref.fsn

    if statut == "RUPTURE" and ved == "Vital":
        return 0  # HORS PLAFOND — traité séparément, jamais via cette liste
    if statut == "CRITIQUE" and ved == "Vital":
        return 1  # ligne de sécurité, quelle que soit la classe/rotation
    if statut == "RUPTURE" and classe == "A" and fsn == "Fast":
        return 2
    if statut == "RUPTURE" and classe == "A" and fsn == "Slow":
        return 3
    if statut == "RUPTURE" and classe == "B" and fsn == "Fast":
        return 4
    if statut == "CRITIQUE" and classe == "A" and fsn == "Fast":
        return 5
    if statut == "CRITIQUE" and classe == "A" and fsn == "Slow":
        return 6
    if statut == "CRITIQUE" and classe == "B" and fsn == "Fast":
        return 7
    return 8  # le reste : COMMANDER (A/B/C), CRITIQUE/RUPTURE classe C, etc.


def _qte_effective(ref: Reference) -> float:
    """
    Quantité réellement retenue : celle saisie manuellement par le pharmacien
    (section 6.7) si renseignée, sinon la suggestion du moteur.
    """
    if ref.qte_a_commander_override is not None:
        return ref.qte_a_commander_override
    return ref.qte_a_commander or 0.0


def _valeur_fcfa(ref: Reference) -> float:
    return _qte_effective(ref) * (ref.prix_cession or 0.0)


def _ligne(ref: Reference, hors_plafond: bool = False) -> dict:
    return {
        "id": str(ref.id),
        "code": ref.code,
        "designation": ref.designation,
        "classe": ref.classe,
        "statut": ref.statut,
        "ved": ref.ved,
        "stock_actuel": ref.stock_actuel or 0.0,
        "qte_a_commander": _qte_effective(ref),
        "qte_a_commander_auto": ref.qte_a_commander or 0.0,
        "qte_a_commander_override": ref.qte_a_commander_override,
        "inclusion_manuelle": ref.inclusion_manuelle,
        "valeur_fcfa": round(_valeur_fcfa(ref), 0),
        "hors_plafond": hors_plafond,
    }


def prioriser_et_plafonner(references: list[Reference], plafond: Optional[float]) -> dict:
    """
    Applique la priorisation et le plafond aux références actionnables.
    plafond=None ou <=0 : pas de restriction, tout est renvoyé dans "inclus".
    """
    # Section 6.7 : le pharmacien garde toujours la main — une référence
    # exclue manuellement disparaît de la commande, une référence incluse
    # manuellement y apparaît même si le moteur ne la juge pas actionnable.
    actionnables = [
        r for r in references
        if r.inclusion_manuelle == "inclure" or (r.statut in STATUTS_ACTIONNABLES and r.inclusion_manuelle != "exclure")
    ]

    # Une inclusion manuelle ("inclure") est une garantie explicite du
    # pharmacien : elle doit vraiment passer hors plafond, pas seulement
    # entrer dans le tri par priorité (où le plafond pourrait quand même la
    # reporter) — sinon les boutons "Inclure quand même (hors plafond)" et
    # "Commander ces références" (encart 7.0) n'auraient aucun effet visible
    # sur une référence déjà actionnable.
    def _hors_plafond(r):
        return (r.statut == "RUPTURE" and r.ved == "Vital") or r.inclusion_manuelle == "inclure"

    hors_plafond_refs = [r for r in actionnables if _hors_plafond(r)]
    reste = [r for r in actionnables if not _hors_plafond(r)]
    # Tri secondaire par valeur FCFA décroissante : départage les références
    # d'un même niveau de priorité (surtout le niveau 8 "le reste", qui
    # regroupe des statuts/classes hétérogènes — section 6.7 V7).
    reste.sort(key=lambda r: (_priorite(r), -_valeur_fcfa(r)))

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
