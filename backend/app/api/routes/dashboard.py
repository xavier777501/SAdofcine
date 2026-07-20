from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
import io

from app.api.deps import get_current_officine
from app.core.database import get_db
from app.models.officine import Officine
from app.models.reference import Reference
from app.models.vente_mensuelle import VenteMensuelle
from app.schemas.dashboard import (
    KpisOut,
    LigneActionOut,
    VenteM1Out,
    LigneNePasCommanderOut,
    CommandePlafonneeOut,
    AlertesStrategiquesOut,
)
from app.services.texte_decision import generer_texte
from app.services.export_dashboard import generer_xlsx, generer_pdf
from app.services.plafond_commande import prioriser_et_plafonner
from app.services.calcul_officine import get_or_create_parametres
from app.services.alertes_strategiques import calculer_alertes_strategiques, references_qualifiees_id

router = APIRouter(prefix="/dashboard", tags=["Tableau de pilotage"])

STATUT_ORDRE = {"RUPTURE": 0, "CRITIQUE": 1, "COMMANDER": 2}
CLASSE_ORDRE = {"A": 0, "B": 1, "C": 2}


def _lignes_action(officine_id, db: Session, filtrer_dans_import: bool = False) -> list[dict]:
    """
    Construit la liste d'action triée par urgence.
    `filtrer_dans_import` (section 4ter, Mode 2 "commande ciblée") : ne
    restreint que le périmètre de cette liste, jamais l'historique ni les
    calculs — donc jamais utilisé pour l'encart 7.0 (alertes stratégiques).
    """
    statut_actionnable = Reference.statut.in_(["RUPTURE", "CRITIQUE", "COMMANDER"])
    conditions = [Reference.officine_id == officine_id]
    if filtrer_dans_import:
        # Une inclusion manuelle est une garantie explicite du pharmacien :
        # elle passe toujours, même hors périmètre ciblé (section 4ter) —
        # seules les références actionnables "normales" sont restreintes au
        # fichier importé.
        conditions.append(or_(
            Reference.inclusion_manuelle == "inclure",
            statut_actionnable & Reference.dans_dernier_import_commande.is_(True),
        ))
    else:
        conditions.append(or_(statut_actionnable, Reference.inclusion_manuelle == "inclure"))

    refs = db.query(Reference).filter(*conditions).all()

    # US-D8 : une référence Non-moving non Vitale a sa quantité neutralisée à 0
    # et n'a donc rien à faire dans la liste d'action (section 7 du cahier des charges).
    refs = [r for r in refs if not (r.fsn == "Non-moving" and r.ved != "Vital")]

    # Section 6.7 : le pharmacien garde toujours la main — une exclusion
    # manuelle retire la référence de la liste, quel que soit son statut.
    refs = [r for r in refs if r.inclusion_manuelle != "exclure"]

    ref_ids = [r.id for r in refs]
    ventes_m1_rows = (
        db.query(VenteMensuelle)
        .filter(VenteMensuelle.reference_id.in_(ref_ids), VenteMensuelle.mois_index == 1)
        .all()
    )
    ventes_m1 = {str(v.reference_id): v.quantite or 0.0 for v in ventes_m1_rows}

    lignes = []
    for r in refs:
        qte_auto = r.qte_a_commander or 0.0
        qte = r.qte_a_commander_override if r.qte_a_commander_override is not None else qte_auto
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
            "sorties_derniere_commande": r.sorties_derniere_commande,
            "statut":        r.statut,
            "qte_a_commander": qte,
            "qte_a_commander_auto": qte_auto,
            "qte_a_commander_override": r.qte_a_commander_override,
            "inclusion_manuelle": r.inclusion_manuelle,
            "valeur_fcfa":   valeur,
            "texte_decision": (
                "Ajouté manuellement à la commande par le pharmacien."
                if r.inclusion_manuelle == "inclure" and r.statut not in ("RUPTURE", "CRITIQUE", "COMMANDER")
                else generer_texte(r.statut, r.ved, r.fsn)
            ),
        })

    # Section 7.1 (V7) : à l'intérieur d'un même statut, tri secondaire par
    # classe ABC puis, à classe égale, par valeur FCFA décroissante — sinon
    # une référence classe C à faible enjeu peut apparaître avant une
    # référence classe A à fort impact au sein d'un même statut.
    lignes.sort(key=lambda l: (
        STATUT_ORDRE.get(l["statut"], 99),
        CLASSE_ORDRE.get(l["classe"], 3),
        -l["valeur_fcfa"],
    ))
    return lignes


# ── Encart d'alerte "Références stratégiques manquées" (section 7.0) ────────
# Priorité absolue d'affichage : jamais scopé par le mode de commande ciblée
# (section 4ter) — toujours l'historique complet, quel que soit ce réglage.

@router.get("/alertes-strategiques", response_model=AlertesStrategiquesOut)
def get_alertes_strategiques(
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    return calculer_alertes_strategiques(officine.id, db)


@router.post("/alertes-strategiques/inclure-tout")
def inclure_tout_alertes_strategiques(
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """
    Bouton "Commander ces références" (section 7.0) : force la présence de
    toutes les références actuellement qualifiées dans la liste de commande,
    via le mécanisme d'arbitrage manuel déjà existant (section 6.7) — donc
    même hors plafond ou hors périmètre ciblé.
    """
    ids = references_qualifiees_id(officine.id, db)
    if ids:
        db.query(Reference).filter(Reference.id.in_(ids)).update(
            {Reference.inclusion_manuelle: "inclure"}, synchronize_session=False
        )
        db.commit()
    return {"nb_references_incluses": len(ids)}


# ── US-E1 : KPIs ─────────────────────────────────────────────────────────────

@router.get("/kpis", response_model=KpisOut)
def get_kpis(
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """Retourne les 5 indicateurs clés recalculés à chaque appel."""
    # params/commit AVANT le chargement des références : db.commit() expire
    # tous les objets déjà chargés dans la session, ce qui forcerait sinon un
    # SELECT individuel par référence (N+1) dès leur premier accès juste après
    # (mesuré : ~8s sur 7900 références, contre <1s en chargeant après coup).
    params = get_or_create_parametres(officine.id, db)
    db.commit()

    refs = db.query(Reference).filter(Reference.officine_id == officine.id).all()

    # US-D8 : les Non-moving non Vitales sont neutralisées, donc exclues des
    # comptes actionnables — sinon les tuiles ne correspondraient plus à la liste.
    actionnables = [r for r in refs if not (r.fsn == "Non-moving" and r.ved != "Vital")]

    # Section 4ter : en mode "commande ciblée", les tuiles de commande (pas le
    # nombre total de références du catalogue) ne portent que sur le périmètre
    # du dernier import de commande — jamais l'encart 7.0, absent de ce calcul.
    if params.mode_commande_ciblee:
        actionnables = [r for r in actionnables if r.dans_dernier_import_commande]

    nb_rupture   = sum(1 for r in actionnables if r.statut == "RUPTURE")
    nb_critique  = sum(1 for r in actionnables if r.statut == "CRITIQUE")
    nb_commander = sum(1 for r in actionnables if r.statut == "COMMANDER")

    # La valeur affichée doit être celle qui sera réellement commandée : on
    # applique donc le même plafond budgétaire (et les mêmes arbitrages
    # manuels) que la Liste d'action et "Quoi commander" — sinon le Tableau
    # de bord annonce un montant que le plafond empêchera de commander
    # (section 6.7 : les deux écrans doivent raconter la même histoire).
    plafonnee = prioriser_et_plafonner(actionnables, params.plafond_commande_fcfa)
    valeur = plafonnee["budget_utilise"] + sum(l["valeur_fcfa"] for l in plafonnee["hors_plafond"])

    tresorerie = sum(r.tresorerie_liberee or 0.0 for r in refs)

    return KpisOut(
        nb_references=len(refs),
        nb_rupture=nb_rupture,
        nb_critique=nb_critique,
        nb_commander=nb_commander,
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
    params = get_or_create_parametres(officine.id, db)
    db.commit()
    return _lignes_action(officine.id, db, filtrer_dans_import=params.mode_commande_ciblee)


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


# ── Produits à ne pas commander (rotation morte ou stock excédentaire) ───────

@router.get("/a-ne-pas-commander", response_model=list[LigneNePasCommanderOut])
def get_a_ne_pas_commander(
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """
    Liste des références qu'il ne faut PAS réapprovisionner pour l'instant :
    - rotation quasi nulle (Non-moving, hors Vital qui reste prudemment recommandé
      à 1 unité — US-D8) ;
    - ou stock largement supérieur au besoin réel (trésorerie immobilisée > 0).
    Triée par montant immobilisé décroissant : les plus gros freins de trésorerie
    d'abord (section 7 du cahier des charges — argument "trésorerie libérée",
    ici détaillé référence par référence plutôt qu'en un seul total agrégé).
    """
    refs = db.query(Reference).filter(Reference.officine_id == officine.id).all()

    # Déjà dans la liste d'action (à commander) : ne peut pas aussi être "à ne pas commander".
    refs = [r for r in refs if r.statut not in ("RUPTURE", "CRITIQUE", "COMMANDER")]

    lignes = []
    for r in refs:
        tresorerie = r.tresorerie_liberee or 0.0
        rotation_morte = r.fsn == "Non-moving" and r.ved != "Vital"

        if not rotation_morte and tresorerie <= 0:
            continue

        if rotation_morte:
            motif = "Ce produit ne s'est presque pas vendu récemment — mieux vaut ne pas le réapprovisionner."
        else:
            motif = "Vous avez déjà plus de stock que nécessaire sur ce produit — inutile d'en recommander pour l'instant."

        lignes.append({
            "code": r.code,
            "designation": r.designation,
            "stock_actuel": r.stock_actuel or 0.0,
            # Valeur exacte, non arrondie ici : arrondir ligne par ligne puis
            # additionner décale le total affiché par rapport à celui du
            # Tableau de bord (qui arrondit une seule fois, sur la somme).
            # L'arrondi à l'affichage (formatFCFA) suffit pour la lisibilité.
            "tresorerie_immobilisee": tresorerie,
            "motif": motif,
        })

    lignes.sort(key=lambda l: l["tresorerie_immobilisee"], reverse=True)
    return lignes


# ── Plafond budgétaire de commande (section 6.7) ─────────────────────────────

@router.get("/commande-plafonnee", response_model=CommandePlafonneeOut)
def get_commande_plafonnee(
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """
    Applique le plafond budgétaire de commande (réglages) aux références
    actionnables : les ruptures sur produits Vitaux sont toujours incluses
    hors plafond, les autres sont sélectionnées par ordre de priorité jusqu'à
    atteindre le plafond, le reste est reporté à la prochaine commande.
    """
    params = get_or_create_parametres(officine.id, db)
    db.commit()

    refs = db.query(Reference).filter(Reference.officine_id == officine.id).all()
    if params.mode_commande_ciblee:
        refs = [r for r in refs if r.dans_dernier_import_commande]
    return prioriser_et_plafonner(refs, params.plafond_commande_fcfa)


# ── US-E4 : Export PDF / XLSX ─────────────────────────────────────────────────

@router.get("/export")
def export_liste_action(
    format: str = Query(..., pattern="^(pdf|xlsx)$"),
    statut: str | None = Query(None, pattern="^(RUPTURE|CRITIQUE|COMMANDER)$"),
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """
    Exporte la liste d'action en PDF ou XLSX.
    Usage : GET /dashboard/export?format=pdf  ou  ?format=xlsx
    `statut` (optionnel) : n'exporte que les références de cet onglet
    (Rupture/Critique/Commander) — doit refléter le filtre actif à l'écran,
    sinon l'export ne correspond pas à ce que le pharmacien regarde.
    """
    params = get_or_create_parametres(officine.id, db)
    db.commit()
    lignes = _lignes_action(officine.id, db, filtrer_dans_import=params.mode_commande_ciblee)
    if statut:
        lignes = [l for l in lignes if l["statut"] == statut]
    nom = officine.nom
    suffixe = f"_{statut.lower()}" if statut else ""

    if format == "xlsx":
        contenu = generer_xlsx(lignes, nom)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"sad_officine_liste_action{suffixe}_{nom}.xlsx"
    else:
        contenu = generer_pdf(lignes, nom)
        media_type = "application/pdf"
        filename = f"sad_officine_liste_action{suffixe}_{nom}.pdf"

    return StreamingResponse(
        io.BytesIO(contenu),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
