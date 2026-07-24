"""
Encart d'alerte "Références stratégiques manquées" — section 7.0 du cahier
des charges V7. Priorité absolue d'affichage sur le tableau de pilotage :
révèle les références classe A/B en RUPTURE/CRITIQUE et estime la vente
perdue en FCFA. Jamais scopé par le mode de commande ciblée (section 4ter) —
toujours calculé sur l'historique complet, quel que soit le périmètre de la
commande en cours.
"""
from __future__ import annotations

import math
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.import_log import ImportLog
from app.models.reference import Reference
from app.services.rupture_fournisseur import doit_etre_masquee

CLASSES_CONCERNEES = ("A", "B")
STATUTS_CONCERNES = ("RUPTURE", "CRITIQUE")


def _jours_rupture(ref: Reference, date_dernier_import: datetime | None) -> int:
    """
    Section 7.0 : RUPTURE (stock=0) -> jours depuis le dernier import (proxy du
    moment où la rupture a été constatée, faute de date de passage à zéro
    suivie). CRITIQUE -> (PC - stock actuel) / (CMM/30), arrondi à l'entier
    supérieur. Toujours >= 0 (un import du jour même donne 0, pas négatif).
    """
    if ref.statut == "RUPTURE":
        if date_dernier_import is None:
            return 0
        return max(0, (datetime.utcnow() - date_dernier_import).days)

    cmm_jour = (ref.cmm or 0.0) / 30.0
    if cmm_jour <= 0:
        return 0
    pc = ref.pc or 0.0
    stock = ref.stock_actuel or 0.0
    return max(0, math.ceil((pc - stock) / cmm_jour))


def calculer_alertes_strategiques(officine_id, db: Session) -> dict:
    """
    Retourne les références classe A/B en RUPTURE/CRITIQUE (hors Non-moving,
    exclusion totale y compris les Vital — contrairement à l'exclusion
    habituelle qui les préserve ailleurs, section 7.0), triées par vente
    perdue estimée décroissante, avec le total et le compte.
    """
    dernier_import = (
        db.query(ImportLog)
        .filter(ImportLog.officine_id == officine_id)
        .order_by(ImportLog.created_at.desc())
        .first()
    )
    date_dernier_import = dernier_import.created_at if dernier_import else None

    refs = (
        db.query(Reference)
        .filter(
            Reference.officine_id == officine_id,
            Reference.classe.in_(CLASSES_CONCERNEES),
            Reference.statut.in_(STATUTS_CONCERNES),
            or_(Reference.fsn != "Non-moving", Reference.fsn.is_(None)),
        )
        .all()
    )

    # Section 6.8 : une référence en attente fournisseur ne doit pas
    # gonfler artificiellement le compte de "produits ratés" — il n'y a rien
    # que le pharmacien puisse faire dans l'immédiat (sauf RUPTURE + Vital).
    refs = [r for r in refs if not doit_etre_masquee(r)]

    lignes = []
    for r in refs:
        jours = _jours_rupture(r, date_dernier_import)
        ventes_perdues = round((r.cmm or 0.0) / 30.0 * jours * (r.prix_public or 0.0), 0)
        lignes.append({
            "id": str(r.id),
            "code": r.code,
            "designation": r.designation,
            "classe": r.classe,
            "statut": r.statut,
            "jours_rupture": jours,
            "ventes_perdues_fcfa": ventes_perdues,
        })

    lignes.sort(key=lambda l: l["ventes_perdues_fcfa"], reverse=True)

    return {
        "references": lignes,
        "nb_references": len(lignes),
        "ventes_perdues_totales_fcfa": round(sum(l["ventes_perdues_fcfa"] for l in lignes), 0),
    }


def references_qualifiees_id(officine_id, db: Session) -> list:
    """Les mêmes critères que calculer_alertes_strategiques, mais renvoie les ids bruts."""
    refs = (
        db.query(Reference)
        .filter(
            Reference.officine_id == officine_id,
            Reference.classe.in_(CLASSES_CONCERNEES),
            Reference.statut.in_(STATUTS_CONCERNES),
            or_(Reference.fsn != "Non-moving", Reference.fsn.is_(None)),
        )
        .all()
    )
    refs = [r for r in refs if not doit_etre_masquee(r)]
    return [r.id for r in refs]
