from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_officine, get_current_user
from app.core.database import get_db
from app.core.security import verify_password
from app.models.column_mapping import ColumnMapping
from app.models.commande_validee import CommandeValidee
from app.models.delai_circuit import DelaiCircuit
from app.models.import_log import ImportLog
from app.models.officine import Officine
from app.models.parametre_officine import ParametreOfficine
from app.models.reference import Reference
from app.models.user import User
from app.models.vente_mensuelle import VenteMensuelle
from app.schemas.delai_circuit import DelaiCircuitOut, DelaiCircuitUpdate
from app.schemas.parametres import ParametreOfficineOut, ParametreOfficineUpdate, ReinitialisationRequest
from app.services.calcul_officine import calculer_toutes_references, get_or_create_parametres, recalculer_apres_commande

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


@router.post("/reinitialiser")
def reinitialiser_donnees_officine(
    data: ReinitialisationRequest,
    officine: Officine = Depends(get_current_officine),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Réinitialisation complète et irréversible : efface toutes les données
    métier de l'officine (références, historique de ventes, imports,
    réglages, mappages, traçabilité des commandes), pour repartir de zéro —
    par exemple pour une démo ou un nouveau client sur la même installation.

    Le compte utilisateur et l'officine elle-même sont conservés : la
    connexion reste valide après la réinitialisation. Le mot de passe est
    exigé pour confirmer, une action de cette ampleur ne devant jamais
    pouvoir être déclenchée par erreur (ex. double-clic, script).
    """
    if not verify_password(data.mot_de_passe, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mot de passe incorrect.",
        )

    ref_ids = [r.id for r in db.query(Reference.id).filter(Reference.officine_id == officine.id).all()]
    if ref_ids:
        db.query(VenteMensuelle).filter(VenteMensuelle.reference_id.in_(ref_ids)).delete(synchronize_session=False)
    db.query(Reference).filter(Reference.officine_id == officine.id).delete(synchronize_session=False)
    db.query(ImportLog).filter(ImportLog.officine_id == officine.id).delete(synchronize_session=False)
    db.query(ColumnMapping).filter(ColumnMapping.officine_id == officine.id).delete(synchronize_session=False)
    db.query(DelaiCircuit).filter(DelaiCircuit.officine_id == officine.id).delete(synchronize_session=False)
    db.query(CommandeValidee).filter(CommandeValidee.officine_id == officine.id).delete(synchronize_session=False)
    db.query(ParametreOfficine).filter(ParametreOfficine.officine_id == officine.id).delete(synchronize_session=False)
    db.commit()

    return {"message": "Toutes les données de l'officine ont été réinitialisées."}


@router.post("/reinitialiser-historique")
def reinitialiser_historique(
    data: ReinitialisationRequest,
    officine: Officine = Depends(get_current_officine),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Réinitialise uniquement les données issues de l'import Type 1
    (historique) : CMM/CMMax/sigma/classe ABC/statut FSN/VED et les 12 mois
    de ventes — comme si aucun import historique n'avait jamais été fait.
    Ne touche ni au stock actuel, ni aux imports Type 2/3, ni aux réglages.
    """
    if not verify_password(data.mot_de_passe, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Mot de passe incorrect.")

    ref_ids = [r.id for r in db.query(Reference.id).filter(Reference.officine_id == officine.id).all()]
    if ref_ids:
        db.query(VenteMensuelle).filter(VenteMensuelle.reference_id.in_(ref_ids)).delete(synchronize_session=False)

    db.query(Reference).filter(Reference.officine_id == officine.id).update(
        {
            Reference.cmm: None,
            Reference.cmmax: None,
            Reference.sigma: None,
            Reference.z_service: None,
            Reference.ss: None,
            Reference.pc: None,
            Reference.eoq: None,
            Reference.ss_periodique: None,
            Reference.niveau_recompletement: None,
            Reference.qte_a_commander: None,
            Reference.statut: None,
            Reference.couverture_jours: None,
            Reference.tresorerie_liberee: None,
            Reference.classe: None,
            Reference.fsn: None,
            Reference.ved: None,
        },
        synchronize_session=False,
    )
    db.commit()

    return {"message": "Historique réinitialisé — refaites vos 12 imports mensuels."}


@router.post("/reinitialiser-stock")
def reinitialiser_stock(
    data: ReinitialisationRequest,
    officine: Officine = Depends(get_current_officine),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Réinitialise uniquement le stock issu des imports Type 2 (commande) et
    Type 3 (réception) : stock actuel remis à 0 pour toutes les références,
    sorties de la dernière commande effacées, mode ciblé désactivé — comme
    si aucun import de commande/réception n'avait jamais été fait. Ne touche
    ni à l'historique (CMM/sigma/classe/FSN/VED), ni aux autres réglages.
    """
    if not verify_password(data.mot_de_passe, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Mot de passe incorrect.")

    db.query(Reference).filter(Reference.officine_id == officine.id).update(
        {
            Reference.stock_actuel: 0,
            Reference.sorties_derniere_commande: None,
            Reference.dans_dernier_import_commande: False,
        },
        synchronize_session=False,
    )

    params = get_or_create_parametres(officine.id, db)
    params.mode_commande_ciblee = False
    db.flush()

    recalculer_apres_commande(officine.id, db)
    db.commit()

    return {"message": "Stock réinitialisé — refaites un import de commande ou de réception."}


@router.post("/reinitialiser-journal")
def reinitialiser_journal(
    data: ReinitialisationRequest,
    officine: Officine = Depends(get_current_officine),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Vide uniquement le tableau "Historique des imports" (journal), pour
    repartir avec une liste propre à l'écran — n'affecte ni le stock, ni
    l'historique 12 mois, ni aucun calcul. Réinitialisation "au jour le
    jour", ponctuelle, la plus légère des trois.
    """
    if not verify_password(data.mot_de_passe, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Mot de passe incorrect.")

    db.query(ImportLog).filter(ImportLog.officine_id == officine.id).delete(synchronize_session=False)
    db.commit()

    return {"message": "Historique des imports vidé."}


@router.post("/reinitialiser-inclusions")
def reinitialiser_inclusions(
    data: ReinitialisationRequest,
    officine: Officine = Depends(get_current_officine),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Annule toutes les inclusions et exclusions manuelles (section 6.7) —
    posées produit par produit ou en masse via "Commander ces références"
    (encart 7.0) — ainsi que les quantités ajustées à la main qui vont avec.
    Ne touche ni au stock actuel, ni à l'historique 12 mois, ni au mode
    ciblé : uniquement l'arbitrage manuel du pharmacien, pour repartir sur
    les seules suggestions automatiques du moteur.

    Utile en particulier quand une inclusion manuelle ancienne (posée avant
    l'activation du mode ciblé, ou via un vieux clic sur "Commander ces
    références") fait apparaître des références hors du périmètre ciblé
    dans la Liste d'action — section 4ter, l'inclusion manuelle passe
    toujours, même hors périmètre, donc seul cet arbitrage explique un tel
    écart une fois le mode ciblé lui-même vérifié correct.
    """
    if not verify_password(data.mot_de_passe, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Mot de passe incorrect.")

    db.query(Reference).filter(Reference.officine_id == officine.id).update(
        {
            Reference.inclusion_manuelle: None,
            Reference.qte_a_commander_override: None,
        },
        synchronize_session=False,
    )
    db.commit()

    return {"message": "Inclusions et exclusions manuelles réinitialisées."}
