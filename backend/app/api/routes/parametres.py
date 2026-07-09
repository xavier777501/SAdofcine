from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_officine
from app.core.database import get_db
from app.models.delai_circuit import DelaiCircuit
from app.models.officine import Officine
from app.models.reference import Reference
from app.schemas.delai_circuit import DelaiCircuitOut, DelaiCircuitUpdate
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


@router.get("/circuits", response_model=list[DelaiCircuitOut])
def lister_circuits(
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """
    Liste les circuits fournisseurs détectés dans les références importées
    (local / France / Chine-Inde...), avec leur délai configuré ou, à défaut,
    le délai global de l'officine (section 5/8 du cahier des charges).
    """
    params = get_or_create_parametres(officine.id, db)
    db.commit()

    circuits_presents = [
        c[0] for c in
        db.query(Reference.circuit)
        .filter(Reference.officine_id == officine.id, Reference.circuit.isnot(None), Reference.circuit != "")
        .distinct()
        .all()
    ]

    delais_configures = {
        d.circuit: d
        for d in db.query(DelaiCircuit).filter(DelaiCircuit.officine_id == officine.id).all()
    }

    resultats = []
    for circuit in sorted(circuits_presents):
        d = delais_configures.get(circuit)
        if d:
            resultats.append(DelaiCircuitOut(
                circuit=circuit, dl_moy_jours=d.dl_moy_jours, dl_max_jours=d.dl_max_jours, configure=True,
            ))
        else:
            resultats.append(DelaiCircuitOut(
                circuit=circuit, dl_moy_jours=params.dl_moy_jours, dl_max_jours=params.dl_max_jours, configure=False,
            ))
    return resultats


@router.patch("/circuits/{circuit}", response_model=DelaiCircuitOut)
def modifier_delai_circuit(
    circuit: str,
    data: DelaiCircuitUpdate,
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """
    Configure (ou met à jour) le délai fournisseur d'un circuit spécifique,
    puis relance le moteur de calcul (les références de ce circuit utiliseront
    désormais ce délai au lieu du délai global).
    """
    if data.dl_max_jours < data.dl_moy_jours:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le délai maximum doit être supérieur ou égal au délai moyen.",
        )

    d = db.query(DelaiCircuit).filter(
        DelaiCircuit.officine_id == officine.id,
        DelaiCircuit.circuit == circuit,
    ).first()
    if d is None:
        d = DelaiCircuit(
            officine_id=officine.id, circuit=circuit,
            dl_moy_jours=data.dl_moy_jours, dl_max_jours=data.dl_max_jours,
        )
        db.add(d)
    else:
        d.dl_moy_jours = data.dl_moy_jours
        d.dl_max_jours = data.dl_max_jours

    db.flush()
    calculer_toutes_references(officine.id, db)
    db.commit()
    db.refresh(d)
    return DelaiCircuitOut(circuit=d.circuit, dl_moy_jours=d.dl_moy_jours, dl_max_jours=d.dl_max_jours, configure=True)
