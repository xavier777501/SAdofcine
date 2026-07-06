import json
import tempfile
import os
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
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
from app.services.calcul_officine import calculer_toutes_references
from app.services.file_parser import (
    CHAMPS_CIBLES,
    apply_mapping,
    get_columns,
    parse_file,
)

router = APIRouter(prefix="/imports", tags=["Import de données"])

MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


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
