from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
import io

from datetime import datetime
from uuid import UUID

from app.api.deps import get_current_officine, get_current_user
from app.core.database import get_db
from app.models.officine import Officine
from app.models.user import User
from app.models.reference import Reference
from app.models.vente_mensuelle import VenteMensuelle
from app.schemas.dashboard import (
    KpisOut,
    LigneActionOut,
    VenteM1Out,
    LigneNePasCommanderOut,
    CommandePlafonneeOut,
    AlertesStrategiquesOut,
    LigneEnAttenteOut,
    CommandeValideeOut,
)
from app.services.texte_decision import generer_texte
from app.services.export_dashboard import generer_xlsx, generer_pdf
from app.services.plafond_commande import prioriser_et_plafonner
from app.services.calcul_officine import get_or_create_parametres
from app.services.alertes_strategiques import calculer_alertes_strategiques, references_qualifiees_id
from app.services.rupture_fournisseur import doit_etre_masquee, en_attente_fournisseur
from app.services.tracabilite_commandes import enregistrer_commande_validee, lister_commandes_validees

router = APIRouter(prefix="/dashboard", tags=["Tableau de pilotage"])

STATUT_ORDRE = {"RUPTURE": 0, "CRITIQUE": 1, "COMMANDER": 2}
CLASSE_ORDRE = {"A": 0, "B": 1, "C": 2}


def _lignes_action(officine_id, db: Session, filtrer_dans_import: bool = False) -> list[dict]:
    """
    Construit la liste d'action triée par urgence.
    `filtrer_dans_import` (section 4ter, Mode 2 "commande ciblée") : montre
    TOUTES les références du dernier import de commande, actionnables ou non
    — le pharmacien voit l'état complet de son fichier, pas seulement ce qui
    manque, sinon le nombre affiché ne correspond jamais à celui du fichier
    importé et laisse croire à tort que le mode ciblé ne fonctionne pas.
    Jamais utilisé pour l'encart 7.0 (alertes stratégiques), qui reste sur
    l'historique complet quel que soit ce réglage.
    """
    statut_actionnable = Reference.statut.in_(["RUPTURE", "CRITIQUE", "COMMANDER"])
    conditions = [Reference.officine_id == officine_id]
    if filtrer_dans_import:
        # Une inclusion manuelle est une garantie explicite du pharmacien :
        # elle passe toujours, même hors périmètre ciblé (section 4ter).
        conditions.append(or_(
            Reference.inclusion_manuelle == "inclure",
            Reference.dans_dernier_import_commande.is_(True),
        ))
    else:
        conditions.append(or_(statut_actionnable, Reference.inclusion_manuelle == "inclure"))

    refs = db.query(Reference).filter(*conditions).all()

    # US-D8 : hors mode ciblé, une Non-moving non Vitale a sa quantité
    # neutralisée à 0 et n'a donc rien à faire dans la liste (section 7) —
    # elle est retirée. En mode ciblé, elle reste visible (le pharmacien voit
    # tout son fichier importé) mais son statut affiché passe à OK plus bas,
    # puisque sa quantité à commander est neutralisée à 0.
    if not filtrer_dans_import:
        refs = [r for r in refs if not (r.fsn == "Non-moving" and r.ved != "Vital")]

    # Section 6.7 : le pharmacien garde toujours la main — une exclusion
    # manuelle retire la référence de la liste, quel que soit son statut.
    refs = [r for r in refs if r.inclusion_manuelle != "exclure"]

    # Section 6.8 (V9) : une référence mise en attente fournisseur est
    # reléguée hors de la liste principale (sauf RUPTURE + Vital, jamais
    # masquable) — elle apparaît dans la sous-section dédiée à la place.
    refs = [r for r in refs if not doit_etre_masquee(r)]

    ref_ids = [r.id for r in refs]
    ventes_m1_rows = (
        db.query(VenteMensuelle)
        .filter(VenteMensuelle.reference_id.in_(ref_ids), VenteMensuelle.mois_index == 1)
        .all()
    )
    ventes_m1 = {str(v.reference_id): v.quantite or 0.0 for v in ventes_m1_rows}

    lignes = []
    for r in refs:
        # Neutralisée (US-D8) : sa quantité auto est déjà à 0 en base, mais
        # son statut brut peut encore dire RUPTURE/CRITIQUE — affiché tel
        # quel ce serait incohérent ("Rupture" avec 0 unité à commander), on
        # l'affiche donc comme OK ici, uniquement pour ce périmètre ciblé.
        neutralisee = filtrer_dans_import and r.fsn == "Non-moving" and r.ved != "Vital"
        statut_affiche = "OK" if neutralisee else (r.statut or "OK")

        qte_auto = 0.0 if neutralisee else (r.qte_a_commander or 0.0)
        qte = r.qte_a_commander_override if r.qte_a_commander_override is not None else qte_auto
        valeur = qte * (r.prix_cession or 0.0)

        if statut_affiche not in ("RUPTURE", "CRITIQUE", "COMMANDER"):
            if r.inclusion_manuelle == "inclure":
                texte = "Ajouté manuellement à la commande par le pharmacien."
            elif neutralisee:
                texte = "Produit non-mouvant — aucune commande nécessaire, même si le stock semble bas."
            else:
                texte = "Stock suffisant — rien à commander pour l'instant."
        else:
            texte = generer_texte(statut_affiche, r.ved, r.fsn)

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
            "statut":        statut_affiche,
            "qte_a_commander": qte,
            "qte_a_commander_auto": qte_auto,
            "qte_a_commander_override": r.qte_a_commander_override,
            "inclusion_manuelle": r.inclusion_manuelle,
            "valeur_fcfa":   valeur,
            "texte_decision": texte,
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
        db.query(Reference).filter(
            Reference.officine_id == officine.id, Reference.id.in_(ids)
        ).update({Reference.inclusion_manuelle: "inclure"}, synchronize_session=False)
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

    # Section 6.8 : une référence en attente fournisseur ne doit pas compter
    # dans les tuiles (sauf RUPTURE + Vital) — cohérent avec la liste d'action.
    actionnables = [r for r in actionnables if not doit_etre_masquee(r)]

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

    # Même périmètre que "À ne pas commander" (section 4ter) : sinon cette
    # tuile annoncerait un montant que cette liste ne détaille pas, les deux
    # écrans se contrediraient (même raison que le plafond budgétaire ci-dessus).
    refs_tresorerie = [r for r in refs if r.dans_dernier_import_commande] if params.mode_commande_ciblee else refs
    tresorerie = sum(r.tresorerie_liberee or 0.0 for r in refs_tresorerie)

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


# ── Section 6.8 : références en attente fournisseur ──────────────────────────

@router.get("/en-attente-fournisseur", response_model=list[LigneEnAttenteOut])
def get_en_attente_fournisseur(
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """
    Références actuellement reléguées hors de la liste principale à cause
    d'une mise en attente fournisseur (section 6.8) — pour la sous-section
    dédiée "En attente fournisseur" de la Liste d'action.

    Section 4ter : même périmètre que le tableau principal juste au-dessus —
    en mode ciblé, ne montre que les références du dernier import de
    commande, sinon cette sous-section resterait sur tout le catalogue alors
    que le tableau qu'elle prolonge est déjà restreint (incohérence sur le
    même écran).
    """
    params = get_or_create_parametres(officine.id, db)
    db.commit()

    refs = (
        db.query(Reference)
        .filter(
            Reference.officine_id == officine.id,
            Reference.fournisseur_indisponible_jusqu_au.isnot(None),
        )
        .all()
    )
    if params.mode_commande_ciblee:
        refs = [r for r in refs if r.dans_dernier_import_commande]
    refs = [r for r in refs if doit_etre_masquee(r) and en_attente_fournisseur(r)]

    lignes = []
    for r in refs:
        qte = r.qte_a_commander_override if r.qte_a_commander_override is not None else (r.qte_a_commander or 0.0)
        lignes.append({
            "id": str(r.id),
            "code": r.code,
            "designation": r.designation,
            "classe": r.classe,
            "statut": r.statut,
            "stock_actuel": r.stock_actuel or 0.0,
            "qte_a_commander": qte,
            "valeur_fcfa": qte * (r.prix_cession or 0.0),
            "fournisseur_indisponible_jusqu_au": r.fournisseur_indisponible_jusqu_au.isoformat(),
        })
    lignes.sort(key=lambda l: -l["valeur_fcfa"])
    return lignes


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

    Section 4ter : en mode "commande ciblée", restreinte aux références du
    dernier import de commande, comme le reste de l'application.
    """
    params = get_or_create_parametres(officine.id, db)
    db.commit()

    conditions = [Reference.officine_id == officine.id]
    if params.mode_commande_ciblee:
        conditions.append(Reference.dans_dernier_import_commande.is_(True))
    refs = db.query(Reference).filter(*conditions).all()
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

    Section 4ter : en mode "commande ciblée", restreinte comme le reste de
    l'écran aux références du dernier import de commande — pour rester
    cohérente avec "À commander en priorité" plutôt que de mélanger deux
    périmètres différents sur le même écran.
    """
    params = get_or_create_parametres(officine.id, db)
    db.commit()

    refs = db.query(Reference).filter(Reference.officine_id == officine.id).all()
    if params.mode_commande_ciblee:
        refs = [r for r in refs if r.dans_dernier_import_commande]

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
    statut: str | None = Query(None, pattern="^(RUPTURE|CRITIQUE|COMMANDER|OK)$"),
    classe: str | None = Query(None, pattern="^(A|B|C)$"),
    recherche: str | None = Query(None),
    officine: Officine = Depends(get_current_officine),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Exporte la liste d'action en PDF ou XLSX.
    Usage : GET /dashboard/export?format=pdf  ou  ?format=xlsx
    `statut`, `classe`, `recherche` (tous optionnels) : doivent refléter
    exactement les onglets/filtres actifs à l'écran au moment du clic
    (onglet de statut, onglet de classe ABC, barre de recherche) — sinon le
    fichier téléchargé ne correspond pas à ce que le pharmacien regarde.
    """
    params = get_or_create_parametres(officine.id, db)
    db.commit()
    lignes = _lignes_action(officine.id, db, filtrer_dans_import=params.mode_commande_ciblee)
    if statut:
        lignes = [l for l in lignes if l["statut"] == statut]
    if classe:
        lignes = [l for l in lignes if l["classe"] == classe]
    if recherche:
        q = recherche.strip().lower()
        lignes = [
            l for l in lignes
            if q in (l["code"] or "").lower() or q in (l["designation"] or "").lower()
        ]
    nom = officine.nom
    suffixe_parts = [p for p in (statut.lower() if statut else None, f"classe{classe.lower()}" if classe else None) if p]
    suffixe = f"_{'_'.join(suffixe_parts)}" if suffixe_parts else ""

    # Section 7.3 : chaque export est le moment où le pharmacien consulte la
    # liste avant de passer sa commande — on l'enregistre comme "commande
    # validée". Ne doit jamais faire échouer l'export en cas de souci.
    try:
        enregistrer_commande_validee(officine.id, current_user.id, format, lignes, db)
    except Exception:
        db.rollback()

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


# ── Section 7.3 : historique des commandes validées ──────────────────────────

@router.get("/historique-commandes", response_model=list[CommandeValideeOut])
def get_historique_commandes(
    date_debut: datetime | None = Query(None),
    date_fin: datetime | None = Query(None),
    user_id: UUID | None = Query(None),
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """
    Historique des commandes validées (chaque export PDF/Excel) : qui, quand,
    quantité recommandée par StockAid vs quantité finalement retenue.
    """
    return lister_commandes_validees(
        officine.id, db, date_debut=date_debut, date_fin=date_fin, user_id=user_id,
    )
