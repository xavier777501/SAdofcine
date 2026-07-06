from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_officine
from app.core.database import get_db
from app.models.officine import Officine
from app.schemas.parametres import ParametreOfficineOut, ParametreOfficineUpdate
from app.services.calcul_officine import calculer_toutes_references, get_or_create_parametres

router = APIRouter(prefix="/parametres", tags=["Réglages"])


@router.get("", response_model=ParametreOfficineOut)
def lire_parametres(
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """Retourne les réglages de l'officine (créés avec des valeurs par défaut si absents)."""
    params = get_or_create_parametres(officine.id, db)
    db.commit()
    db.refresh(params)
    return params


@router.patch("", response_model=ParametreOfficineOut)
def modifier_parametres(
    data: ParametreOfficineUpdate,
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """
    Met à jour les réglages fournis (mise à jour partielle) et relance
    automatiquement le moteur de calcul sur toutes les références de l'officine.
    """
    params = get_or_create_parametres(officine.id, db)

    updates = data.model_dump(exclude_unset=True)
    for champ, valeur in updates.items():
        setattr(params, champ, valeur)

    if params.dl_max_jours < params.dl_moy_jours:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le délai maximum doit être supérieur ou égal au délai moyen.",
        )

    db.flush()
    calculer_toutes_references(officine.id, db)
    db.commit()
    db.refresh(params)
    return params
