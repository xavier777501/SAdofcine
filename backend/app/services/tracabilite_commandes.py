"""
Traçabilité des commandes — section 7.3 du cahier des charges V9.
Chaque export de la liste d'action (PDF/Excel) — le moment où le pharmacien
consulte la liste avant de passer sa commande chez le grossiste (section
4bis) — enregistre un instantané : qui, quand, et pour chaque référence la
quantité recommandée par le moteur vs la quantité finalement retenue.
"""
from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.commande_validee import CommandeValidee
from app.models.user import User


def enregistrer_commande_validee(
    officine_id: UUID,
    user_id: UUID | None,
    format: str,
    lignes: list[dict],
    db: Session,
) -> None:
    """Enregistre un instantané de la liste exportée. N'échoue jamais l'export
    en cas de souci : la traçabilité est un plus, pas une condition bloquante."""
    contenu = [
        {
            "code": l["code"],
            "designation": l["designation"],
            "qte_recommandee": l.get("qte_a_commander_auto", l.get("qte_a_commander", 0.0)),
            "qte_validee": l.get("qte_a_commander", 0.0),
        }
        for l in lignes
    ]
    db.add(CommandeValidee(
        officine_id=officine_id,
        user_id=user_id,
        format=format,
        lignes=json.dumps(contenu, ensure_ascii=False),
    ))
    db.commit()


def lister_commandes_validees(
    officine_id: UUID,
    db: Session,
    date_debut=None,
    date_fin=None,
    user_id: UUID | None = None,
) -> list[dict]:
    query = db.query(CommandeValidee).filter(CommandeValidee.officine_id == officine_id)
    if date_debut is not None:
        query = query.filter(CommandeValidee.created_at >= date_debut)
    if date_fin is not None:
        query = query.filter(CommandeValidee.created_at <= date_fin)
    if user_id is not None:
        query = query.filter(CommandeValidee.user_id == user_id)

    commandes = query.order_by(CommandeValidee.created_at.desc()).all()

    user_ids = {c.user_id for c in commandes if c.user_id is not None}
    emails_par_id = {
        u.id: u.email
        for u in db.query(User).filter(User.id.in_(user_ids)).all()
    } if user_ids else {}

    resultats = []
    for c in commandes:
        lignes = json.loads(c.lignes)
        nb_ecarts = sum(1 for l in lignes if l["qte_recommandee"] != l["qte_validee"])
        resultats.append({
            "id": str(c.id),
            "date": c.created_at.isoformat(),
            "utilisateur_email": emails_par_id.get(c.user_id, "—"),
            "format": c.format,
            "nb_references": len(lignes),
            "nb_ecarts": nb_ecarts,
            "lignes": lignes,
        })
    return resultats
