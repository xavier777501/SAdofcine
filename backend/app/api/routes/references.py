import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_officine
from app.core.database import get_db
from app.models.officine import Officine
from app.models.reference import Reference
from app.schemas.references import (
    ReferenceOut, VedUpdate, RisqueFournisseurUpdate, AjustementCommandeUpdate,
    FournisseurIndisponibleUpdate,
)
from app.services.calcul_officine import calculer_toutes_references

router = APIRouter(prefix="/references", tags=["Références"])

STATUT_ORDRE = {"RUPTURE": 0, "CRITIQUE": 1, "COMMANDER": 2, "OK": 3}


def _get_reference_ou_404(reference_id: str, officine: Officine, db: Session) -> Reference:
    try:
        rid = uuid.UUID(reference_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Identifiant invalide.")

    ref = db.query(Reference).filter(
        Reference.id == rid,
        Reference.officine_id == officine.id,
    ).first()
    if ref is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Référence introuvable.")
    return ref


@router.get("", response_model=list[ReferenceOut])
def lister_references(
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """Liste toutes les références de l'officine, triées par urgence de statut."""
    refs = db.query(Reference).filter(Reference.officine_id == officine.id).all()
    refs.sort(key=lambda r: STATUT_ORDRE.get(r.statut, 4))
    return refs


@router.patch("/{reference_id}/ved", response_model=ReferenceOut)
def modifier_ved(
    reference_id: str,
    data: VedUpdate,
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """
    US-D9 : attribue un statut VED à une référence (classes A/B uniquement),
    puis relance le moteur de calcul pour appliquer le nouveau facteur Z.
    """
    ref = _get_reference_ou_404(reference_id, officine, db)

    if ref.classe not in ("A", "B"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le statut VED ne peut être attribué qu'aux références de classe A ou B.",
        )

    ref.ved = data.ved
    db.flush()
    calculer_toutes_references(officine.id, db)
    db.commit()
    db.refresh(ref)
    return ref


@router.patch("/{reference_id}/risque-fournisseur", response_model=ReferenceOut)
def modifier_risque_fournisseur(
    reference_id: str,
    data: RisqueFournisseurUpdate,
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """US-D10 : ajoute un nombre de jours de risque fournisseur additionnel par référence."""
    ref = _get_reference_ou_404(reference_id, officine, db)

    ref.risque_fournisseur_jours = data.risque_fournisseur_jours
    db.flush()
    calculer_toutes_references(officine.id, db)
    db.commit()
    db.refresh(ref)
    return ref


@router.patch("/{reference_id}/ajustement-commande", response_model=ReferenceOut)
def modifier_ajustement_commande(
    reference_id: str,
    data: AjustementCommandeUpdate,
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """
    Section 6.7 : le pharmacien garde toujours la main sur la commande — il
    peut forcer l'inclusion ou l'exclusion d'une référence, et/ou remplacer la
    quantité suggérée par le moteur par sa propre quantité. Aucun recalcul du
    moteur n'est nécessaire : c'est un arbitrage manuel, pas une donnée d'entrée.
    """
    ref = _get_reference_ou_404(reference_id, officine, db)

    ref.qte_a_commander_override = data.qte_a_commander_override
    ref.inclusion_manuelle = data.inclusion_manuelle
    db.commit()
    db.refresh(ref)
    return ref


@router.patch("/{reference_id}/fournisseur-indisponible", response_model=ReferenceOut)
def modifier_fournisseur_indisponible(
    reference_id: str,
    data: FournisseurIndisponibleUpdate,
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """
    Section 6.8 : le fournisseur habituel n'a pas non plus la référence en
    stock — le pharmacien la met en attente jusqu'à une date de réévaluation.
    Aucun recalcul du moteur nécessaire : c'est un arbitrage manuel, comme
    l'inclusion/exclusion (section 6.7).
    """
    ref = _get_reference_ou_404(reference_id, officine, db)

    ref.fournisseur_indisponible_jusqu_au = data.date_reevaluation
    db.commit()
    db.refresh(ref)
    return ref
