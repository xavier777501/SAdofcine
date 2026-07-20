import json
import tempfile
import os
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_officine
from app.core.config import settings
from app.core.database import get_db
from app.models.column_mapping import ColumnMapping
from app.models.import_log import ImportLog
from app.models.officine import Officine
from app.models.reference import Reference
from app.models.vente_mensuelle import VenteMensuelle
from app.schemas.imports import ImportLogOut, MappingSave
from app.services.calcul_officine import (
    calculer_toutes_references,
    get_or_create_parametres,
    recalculer_apres_commande,
)
from app.services.file_parser import (
    CHAMPS_CIBLES,
    apply_mapping,
    get_columns,
    parse_file,
    parse_commande_logpharma,
)
from app.services.ved_starter_list import correspond_liste_demarrage

router = APIRouter(prefix="/imports", tags=["Import de données"])

MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


# ─── État de l'historique (pour proposer automatiquement le bon type d'import) ─

@router.get("/etat")
def get_etat_import(
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """
    Indique si l'historique (Type 1) a déjà été initialisé pour cette officine,
    et combien de mois glissants sont déjà remplis (0 à 12). Sert à proposer
    automatiquement le bon type d'import (section 4bis : "il ne doit jamais
    avoir à choisir manuellement"), et à ce que l'écran d'import mensuel se
    souvienne où le pharmacien en est réellement, plutôt que de repartir de
    zéro à chaque fois qu'il rouvre la page.
    """
    historique_initialise = (
        db.query(Reference)
        .filter(Reference.officine_id == officine.id, Reference.cmm.isnot(None))
        .first()
        is not None
    )

    # Nombre de mois déjà remplis = le plus grand nombre de lignes de ventes
    # mensuelles trouvé pour une référence de cette officine (0 à 12).
    ligne_max = (
        db.query(func.count(VenteMensuelle.id))
        .join(Reference, VenteMensuelle.reference_id == Reference.id)
        .filter(Reference.officine_id == officine.id)
        .group_by(VenteMensuelle.reference_id)
        .order_by(func.count(VenteMensuelle.id).desc())
        .first()
    )
    nb_mois_historique = ligne_max[0] if ligne_max else 0

    return {
        "historique_initialise": historique_initialise,
        "nb_mois_historique": nb_mois_historique,
    }


# ─── Mapping de colonnes ─────────────────────────────────────────────────────

@router.get("/mapping")
def get_mapping(
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """Retourne le mappage sauvegardé pour cette officine, ainsi que la liste des champs cibles."""
    rows = db.query(ColumnMapping).filter(ColumnMapping.officine_id == officine.id).all()
    mapping = {r.champ_cible: r.colonne_source for r in rows}
    return {"champs_cibles": CHAMPS_CIBLES, "mapping": mapping}


@router.post("/mapping")
def save_mapping(
    data: MappingSave,
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """Sauvegarde (ou met à jour) le mappage de colonnes pour cette officine."""
    # Supprimer l'ancien mappage
    db.query(ColumnMapping).filter(ColumnMapping.officine_id == officine.id).delete()

    for item in data.mapping:
        if item.colonne_source:
            db.add(ColumnMapping(
                officine_id=officine.id,
                champ_cible=item.champ_cible,
                colonne_source=item.colonne_source,
            ))
    db.commit()
    return {"message": "Mappage sauvegardé."}


# ─── Preview (5 premières lignes) ────────────────────────────────────────────

@router.post("/preview")
async def preview_file(
    file: UploadFile = File(...),
    officine: Officine = Depends(get_current_officine),
):
    """
    Upload temporaire : retourne les 5 premières lignes et la liste des colonnes.
    Ne persiste rien en base. Sert à afficher l'interface de mappage.
    """
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Fichier trop volumineux (max {settings.MAX_UPLOAD_SIZE_MB} Mo).",
        )

    try:
        df = parse_file(content, file.filename or "")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    colonnes = get_columns(df)
    apercu = df.head(5).fillna("").to_dict(orient="records")

    return {"colonnes": colonnes, "apercu": apercu, "nom_fichier": file.filename}


# ─── Import complet ───────────────────────────────────────────────────────────

@router.post("/", response_model=ImportLogOut)
async def import_file(
    file: UploadFile = File(...),
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """
    Import complet :
    1. Parse le fichier avec le mappage sauvegardé de l'officine.
    2. Upsert les références en base (mise à jour si le code existe déjà).
    3. Remplace l'historique des ventes mensuelles.
    4. Crée un ImportLog avec le rapport.
    """
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Fichier trop volumineux (max {settings.MAX_UPLOAD_SIZE_MB} Mo).",
        )

    # Récupérer le mappage sauvegardé
    rows = db.query(ColumnMapping).filter(ColumnMapping.officine_id == officine.id).all()
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucun mappage de colonnes configuré. Faites d'abord un aperçu et sauvegardez le mappage.",
        )
    mapping = {r.champ_cible: r.colonne_source for r in rows}

    # Parser le fichier
    try:
        df = parse_file(content, file.filename or "")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    # Appliquer le mappage
    try:
        lignes_ok, lignes_err = apply_mapping(df, mapping)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    # Créer le log d'import
    import_log = ImportLog(
        officine_id=officine.id,
        nom_fichier=file.filename or "inconnu",
        statut="en_cours",
        nb_lignes_total=len(df),
        nb_lignes_ok=len(lignes_ok),
        nb_lignes_erreur=len(lignes_err),
        erreurs_detail=json.dumps(lignes_err, ensure_ascii=False) if lignes_err else None,
    )
    db.add(import_log)
    db.flush()

    # Upsert des références
    for record in lignes_ok:
        code = record["code"]
        ref = db.query(Reference).filter(
            Reference.officine_id == officine.id,
            Reference.code == code,
        ).first()

        if ref is None:
            ref = Reference(officine_id=officine.id, code=code)
            db.add(ref)

        ref.designation   = record.get("designation") or ref.designation
        ref.forme         = record.get("forme")
        ref.prix_cession  = record.get("prix_cession")
        ref.prix_public   = record.get("prix_public")
        ref.stock_actuel  = record.get("stock_actuel") or 0
        ref.circuit       = record.get("circuit")
        db.flush()  # pour avoir ref.id

        # Remplacer les ventes mensuelles
        db.query(VenteMensuelle).filter(VenteMensuelle.reference_id == ref.id).delete()
        for i in range(1, 13):
            qte = record.get(f"vente_m{i}")
            if qte is not None:
                db.add(VenteMensuelle(
                    reference_id=ref.id,
                    mois_index=i,
                    quantite=qte,
                ))

    # Recalcul automatique du moteur SAD (US-B3)
    calculer_toutes_references(officine.id, db)

    import_log.statut = "succes"
    db.commit()
    db.refresh(import_log)

    return import_log


# ─── Import Type 2 : stock Logpharma ─────────────────────────────────────────

@router.post("/commande", response_model=ImportLogOut)
async def import_commande_logpharma(
    file: UploadFile = File(...),
    mode_ciblee: bool = Form(False),
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """
    Import Type 2 (Logpharma) : parse un export 'Listing de Produit à Commander',
    met à jour le stock_actuel de chaque référence connue, puis recalcule les
    quantités à commander. Format fixe — aucun mappage de colonnes nécessaire.

    Ne touche jamais CMM/sigma/classe ABC/FSN/prix : le cahier des charges est
    explicite (section 4bis) — "il ne met à jour que le stock actuel". Ces
    données de fond du moteur ne viennent que de l'import historique.

    Les sorties de la période sont aussi lues et conservées par référence
    (affichées au pharmacien sur la liste d'action) et sommées pour ce rapport
    d'import, afin de détailler ce qui s'est vendu depuis la dernière commande.

    `mode_ciblee` (section 4ter) : mémorisé sur l'officine et n'affecte que le
    périmètre de la liste de commande générée ensuite (et du plafond) — jamais
    l'historique, les calculs, ni l'encart d'alerte 7.0 (toujours plein périmètre).
    """
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Fichier trop volumineux (max {settings.MAX_UPLOAD_SIZE_MB} Mo).",
        )

    try:
        lignes = parse_commande_logpharma(content)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    params = get_or_create_parametres(officine.id, db)
    params.mode_commande_ciblee = mode_ciblee

    # Repart de zéro à chaque import de commande : seules les références
    # effectivement présentes dans CE fichier doivent porter le drapeau.
    db.query(Reference).filter(Reference.officine_id == officine.id).update(
        {Reference.dans_dernier_import_commande: False}, synchronize_session=False
    )

    nb_ok = 0
    nb_err = 0
    erreurs: list[dict] = []
    sorties_totales = 0.0

    for ligne in lignes:
        ref = db.query(Reference).filter(
            Reference.officine_id == officine.id,
            Reference.code == ligne["code"],
        ).first()

        if ref is None:
            nb_err += 1
            erreurs.append({"ligne": ligne["code"], "raison": "Code introuvable dans votre base"})
            continue

        sorties = max(0.0, ligne.get("sorties_periode") or 0.0)
        ref.stock_actuel = ligne["stock_actuel"]
        ref.sorties_derniere_commande = sorties
        ref.dans_dernier_import_commande = True
        sorties_totales += sorties
        nb_ok += 1

    recalculer_apres_commande(officine.id, db)

    import_log = ImportLog(
        officine_id=officine.id,
        nom_fichier=file.filename or "inconnu",
        statut="succes",
        nb_lignes_total=len(lignes),
        nb_lignes_ok=nb_ok,
        nb_lignes_erreur=nb_err,
        erreurs_detail=json.dumps(erreurs, ensure_ascii=False) if erreurs else None,
        sorties_totales=round(sorties_totales, 0),
    )
    db.add(import_log)
    db.commit()
    db.refresh(import_log)

    return import_log


# ─── Import Type 1 : historique mensuel, un mois Logpharma à la fois ────────────

@router.post("/historique-logpharma", response_model=ImportLogOut)
async def import_historique_logpharma(
    file: UploadFile = File(...),
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """
    Import Type 1 (historique), mécanisme glissant conforme au cahier des
    charges (section 4bis) : "à chaque import, le mois le plus ancien sort de
    l'historique et le nouveau mois entre". Logpharma ne fournit pas de fichier
    "12 mois glissants" tout prêt avec une colonne par mois — son export natif
    ("Listing de Produit à Commander") ne donne qu'un total de sorties pour la
    période demandée. On réutilise donc ce même format fixe, et chaque import
    représente automatiquement le nouveau mois le plus récent (M-1) : tout
    l'historique existant glisse d'un cran (M-1→M-2, ..., et M-12 sort
    définitivement), sans que le pharmacien ait à préciser quel mois c'est.

    Pour l'initialisation, répéter cet import jusqu'à 12 fois, du mois le plus
    ancien au plus récent, pour reconstituer l'historique glissant complet.
    Chaque import met aussi à jour le stock actuel, puisqu'il représente
    toujours le mois le plus récent au moment où il est réalisé.
    """
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Fichier trop volumineux (max {settings.MAX_UPLOAD_SIZE_MB} Mo).",
        )

    try:
        lignes = parse_commande_logpharma(content)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    # Même logique que /imports/etat : capturée AVANT ce traitement, car il
    # va lui-même poser des CMM et rendrait le test faussement positif après coup.
    premier_import_historique = (
        db.query(Reference)
        .filter(Reference.officine_id == officine.id, Reference.cmm.isnot(None))
        .first()
        is None
    )

    # Faire glisser l'historique d'un cran pour TOUTES les références déjà
    # connues de l'officine, avant d'insérer le nouveau mois : le mois 12
    # (le plus ancien) sort, chaque mois restant avance d'un rang.
    ref_ids_existantes = [
        r.id for r in db.query(Reference.id).filter(Reference.officine_id == officine.id).all()
    ]
    if ref_ids_existantes:
        db.query(VenteMensuelle).filter(
            VenteMensuelle.reference_id.in_(ref_ids_existantes),
            VenteMensuelle.mois_index == 12,
        ).delete(synchronize_session=False)
        db.query(VenteMensuelle).filter(
            VenteMensuelle.reference_id.in_(ref_ids_existantes),
        ).update({VenteMensuelle.mois_index: VenteMensuelle.mois_index + 1}, synchronize_session=False)
        db.flush()

    nb_ok = 0
    nb_err = 0
    erreurs: list[dict] = []

    for ligne in lignes:
        code = ligne["code"]
        ref = db.query(Reference).filter(
            Reference.officine_id == officine.id,
            Reference.code == code,
        ).first()

        if ref is None:
            designation = ligne.get("designation")
            if not designation:
                nb_err += 1
                erreurs.append({
                    "ligne": code,
                    "raison": "Référence inconnue et sans désignation — impossible de la créer.",
                })
                continue
            ref = Reference(officine_id=officine.id, code=code, designation=designation, stock_actuel=0)
            db.add(ref)
        elif ligne.get("designation"):
            ref.designation = ligne["designation"]

        if ligne.get("prix_cession") is not None:
            ref.prix_cession = ligne["prix_cession"]
        if ligne.get("prix_public") is not None:
            ref.prix_public = ligne["prix_public"]
        if ligne.get("circuit"):
            ref.circuit = ligne["circuit"]

        # Cet import représente toujours le mois le plus récent : le stock
        # actuel est mis à jour à chaque fois.
        ref.stock_actuel = ligne["stock_actuel"]

        db.flush()  # pour avoir ref.id

        # Sorties négatives (corrections d'inventaire) exclues du calcul (section 6.1).
        quantite = max(0.0, ligne.get("sorties_periode") or 0.0)
        # Le décalage ci-dessus a déjà vidé le mois_index=1 pour cette
        # référence (poussé vers 2) — jamais de doublon possible ici.
        db.add(VenteMensuelle(reference_id=ref.id, mois_index=1, quantite=quantite))

        nb_ok += 1

    # Recalcul complet du moteur SAD (CMM/sigma/ABC/FSN/SS/PC dépendent des 12 mois)
    calculer_toutes_references(officine.id, db)

    if premier_import_historique:
        # Section 6.6 : pré-remplissage automatique du VED au premier import,
        # une fois les classes ABC connues (le VED ne concerne que A/B — les
        # références déjà renseignées manuellement ne sont jamais écrasées).
        refs_ab = (
            db.query(Reference)
            .filter(
                Reference.officine_id == officine.id,
                Reference.classe.in_(("A", "B")),
                Reference.ved.is_(None),
            )
            .all()
        )
        for ref in refs_ab:
            if correspond_liste_demarrage(ref.designation):
                ref.ved = "Vital"
        # Le Z de service et donc le SS dépendent du VED : deuxième passe
        # nécessaire pour que la ligne de sécurité "CRITIQUE + Vital" soit
        # correcte dès ce premier import (section 6.7).
        db.flush()
        calculer_toutes_references(officine.id, db)

    import_log = ImportLog(
        officine_id=officine.id,
        nom_fichier=file.filename or "inconnu",
        statut="succes",
        nb_lignes_total=len(lignes),
        nb_lignes_ok=nb_ok,
        nb_lignes_erreur=nb_err,
        erreurs_detail=json.dumps(erreurs, ensure_ascii=False) if erreurs else None,
    )
    db.add(import_log)
    db.commit()
    db.refresh(import_log)

    return import_log


# ─── Import Type 1 : fichier annuel combiné (initialisation rapide, dégradée) ──

@router.post("/historique-logpharma-annuel", response_model=ImportLogOut)
async def import_historique_logpharma_annuel(
    file: UploadFile = File(...),
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """
    Import Type 1 à partir d'un unique fichier Logpharma couvrant une longue
    période (ex. l'année entière) en un seul total de sorties par référence —
    même format fixe que les autres imports Logpharma.

    Ne calcule QUE le CMM (= total ÷ 12), seule valeur que la formule du
    cahier des charges (section 6.1, "somme des ventes des 12 derniers mois /
    12") permet de dériver d'un total global. CMMax ("valeur la plus haute
    observée sur les 12 derniers mois") et l'écart-type mensuel (sigma)
    exigent explicitement un détail mois par mois qu'un total unique ne
    contient pas — ils ne sont donc jamais dérivés ni approximés ici, pour ne
    pas fausser le calcul. Sans sigma, le stock de sécurité (SS), le point de
    commande (PC), le statut et la quantité à commander restent indisponibles
    pour ces références tant qu'elles n'ont pas été complétées mois par mois
    via /imports/historique-logpharma — elles n'apparaîtront donc dans aucune
    liste d'action tant que ce n'est pas fait (comportement volontaire, pas un bug).
    """
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Fichier trop volumineux (max {settings.MAX_UPLOAD_SIZE_MB} Mo).",
        )

    try:
        lignes = parse_commande_logpharma(content)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    nb_ok = 0
    nb_err = 0
    erreurs: list[dict] = []

    for ligne in lignes:
        code = ligne["code"]
        ref = db.query(Reference).filter(
            Reference.officine_id == officine.id,
            Reference.code == code,
        ).first()

        if ref is None:
            designation = ligne.get("designation")
            if not designation:
                nb_err += 1
                erreurs.append({
                    "ligne": code,
                    "raison": "Référence inconnue et sans désignation — impossible de la créer.",
                })
                continue
            ref = Reference(officine_id=officine.id, code=code, designation=designation, stock_actuel=0)
            db.add(ref)
        elif ligne.get("designation"):
            ref.designation = ligne["designation"]

        if ligne.get("prix_cession") is not None:
            ref.prix_cession = ligne["prix_cession"]
        if ligne.get("prix_public") is not None:
            ref.prix_public = ligne["prix_public"]
        if ligne.get("circuit"):
            ref.circuit = ligne["circuit"]

        ref.stock_actuel = ligne["stock_actuel"]

        # Sorties négatives (corrections d'inventaire) exclues, section 6.1.
        total_periode = max(0.0, ligne.get("sorties_periode") or 0.0)
        ref.cmm = round(total_periode / 12.0, 1)
        # CMMax, sigma, classe ABC, FSN, SS, PC, statut, qté : volontairement
        # laissés tels quels (None pour une nouvelle référence) — nécessitent
        # un détail mensuel réel, jamais inventés à partir d'un total unique.

        db.flush()
        nb_ok += 1

    import_log = ImportLog(
        officine_id=officine.id,
        nom_fichier=file.filename or "inconnu",
        statut="succes",
        nb_lignes_total=len(lignes),
        nb_lignes_ok=nb_ok,
        nb_lignes_erreur=nb_err,
        erreurs_detail=json.dumps(erreurs, ensure_ascii=False) if erreurs else None,
    )
    db.add(import_log)
    db.commit()
    db.refresh(import_log)

    return import_log


# ─── Historique des imports ───────────────────────────────────────────────────

@router.get("/", response_model=list[ImportLogOut])
def list_imports(
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """Retourne les 20 derniers imports de l'officine."""
    return (
        db.query(ImportLog)
        .filter(ImportLog.officine_id == officine.id)
        .order_by(ImportLog.created_at.desc())
        .limit(20)
        .all()
    )
