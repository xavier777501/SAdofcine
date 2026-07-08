from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
import io

from app.api.deps import get_current_officine
from app.core.database import get_db
from app.models.officine import Officine
from app.models.reference import Reference
from app.models.vente_mensuelle import VenteMensuelle
from app.schemas.dashboard import KpisOut, LigneActionOut, VenteM1Out
from app.services.texte_decision import generer_texte
from app.services.export_dashboard import generer_xlsx, generer_pdf

router = APIRouter(prefix="/dashboard", tags=["Tableau de pilotage"])

STATUT_ORDRE = {"RUPTURE": 0, "CRITIQUE": 1, "COMMANDER": 2}


def _lignes_action(officine_id, db: Session) -> list[dict]:
    """Construit la liste d'action triée par urgence."""
    refs = (
        db.query(Reference)
        .filter(
            Reference.officine_id == officine_id,
            Reference.statut.in_(["RUPTURE", "CRITIQUE", "COMMANDER"]),
        )
        .all()
    )

    # US-D8 : une référence Non-moving non Vitale a sa quantité neutralisée à 0
    # et n'a donc rien à faire dans la liste d'action (section 7 du cahier des charges).
    refs = [r for r in refs if not (r.fsn == "Non-moving" and r.ved != "Vital")]

    ref_ids = [r.id for r in refs]
    ventes_m1_rows = (
        db.query(VenteMensuelle)
        .filter(VenteMensuelle.reference_id.in_(ref_ids), VenteMensuelle.mois_index == 1)
        .all()
    )
    ventes_m1 = {str(v.reference_id): v.quantite or 0.0 for v in ventes_m1_rows}

    lignes = []
    for r in refs:
        qte = r.qte_a_commander or 0.0
        valeur = qte * (r.prix_cession or 0.0)
        lignes.append({
            "id":            str(r.id),
            "code":          r.code,
            "designation":   r.designation,
            "classe":        r.classe,
            "fsn":           r.fsn,
            "ved":           r.ved,
            "stock_actuel":  r.stock_actuel or 0.0,
            "cmm":           r.cmm or 0.0,
            "vente_m1":      ventes_m1.get(str(r.id), 0.0),
            "statut":        r.statut,
            "qte_a_commander": qte,
            "valeur_fcfa":   valeur,
            "texte_decision": generer_texte(r.statut, r.ved, r.fsn),
        })

    lignes.sort(key=lambda l: STATUT_ORDRE.get(l["statut"], 99))
    return lignes


# ── US-E1 : KPIs ─────────────────────────────────────────────────────────────

@router.get("/kpis", response_model=KpisOut)
def get_kpis(
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """Retourne les 5 indicateurs clés recalculés à chaque appel."""
    refs = db.query(Reference).filter(Reference.officine_id == officine.id).all()

    # US-D8 : les Non-moving non Vitales sont neutralisées, donc exclues des
    # comptes actionnables — sinon les tuiles ne correspondraient plus à la liste.
    actionnables = [r for r in refs if not (r.fsn == "Non-moving" and r.ved != "Vital")]

    nb_rupture   = sum(1 for r in actionnables if r.statut == "RUPTURE")
    nb_critique  = sum(1 for r in actionnables if r.statut == "CRITIQUE")
    nb_commander = sum(1 for r in actionnables if r.statut == "COMMANDER")

    valeur = sum(
        (r.qte_a_commander or 0.0) * (r.prix_cession or 0.0)
        for r in actionnables
        if r.statut in ("RUPTURE", "CRITIQUE", "COMMANDER")
    )
    tresorerie = sum(r.tresorerie_liberee or 0.0 for r in refs)

    return KpisOut(
        nb_references=len(refs),
        nb_rupture=nb_rupture,
        nb_critique=nb_critique,
        nb_a_commander=nb_rupture + nb_critique + nb_commander,
        valeur_commande_fcfa=round(valeur, 0),
        tresorerie_liberee_fcfa=round(tresorerie, 0),
    )


# ── US-E2/E3 : Liste d'action avec texte de décision ─────────────────────────

@router.get("/liste-action", response_model=list[LigneActionOut])
def get_liste_action(
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """
    Liste des références à traiter, triées RUPTURE → CRITIQUE → COMMANDER.
    Inclut un texte de décision en langage clair pour chaque référence.
    Les références OK et Non-moving non vitales sont exclues.
    """
    return _lignes_action(officine.id, db)


# ── Ventes du mois dernier (M-1), toutes références confondues ──────────────

@router.get("/ventes-m1", response_model=list[VenteM1Out])
def get_ventes_m1(
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """
    Liste de toutes les références ayant eu au moins une vente le mois dernier
    (M-1), triée par quantité vendue décroissante — indépendamment du statut,
    pour voir ce qui tourne bien (best-sellers) et ce qui reste sur l'étagère.
    """
    refs = db.query(Reference).filter(Reference.officine_id == officine.id).all()
    ref_ids = [r.id for r in refs]

    ventes_rows = (
        db.query(VenteMensuelle)
        .filter(VenteMensuelle.reference_id.in_(ref_ids), VenteMensuelle.mois_index == 1)
        .all()
    )
    ventes_m1 = {str(v.reference_id): v.quantite or 0.0 for v in ventes_rows}

    resultats = []
    for r in refs:
        vm1 = ventes_m1.get(str(r.id), 0.0)
        if vm1 > 0:
            resultats.append({
                "code":            r.code,
                "designation":     r.designation,
                "vente_m1":        vm1,
                "stock_actuel":    r.stock_actuel or 0.0,
                "statut":          r.statut or "OK",
                "qte_a_commander": r.qte_a_commander or 0.0,
            })

    resultats.sort(key=lambda l: l["vente_m1"], reverse=True)
    return resultats


# ── US-E4 : Export PDF / XLSX ─────────────────────────────────────────────────

@router.get("/export")
def export_liste_action(
    format: str = Query(..., pattern="^(pdf|xlsx)$"),
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """
    Exporte la liste d'action en PDF ou XLSX.
    Usage : GET /dashboard/export?format=pdf  ou  ?format=xlsx
    """
    lignes = _lignes_action(officine.id, db)
    nom = officine.nom

    if format == "xlsx":
        contenu = generer_xlsx(lignes, nom)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"sad_officine_liste_action_{nom}.xlsx"
    else:
        contenu = generer_pdf(lignes, nom)
        media_type = "application/pdf"
        filename = f"sad_officine_liste_action_{nom}.pdf"

    return StreamingResponse(
        io.BytesIO(contenu),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
