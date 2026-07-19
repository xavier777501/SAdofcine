"""
Orchestration du calcul SAD pour une officine complète.
Récupère les données en BDD, appelle les fonctions pures de moteur_sad,
et persiste les résultats sur chaque référence.
"""
from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.delai_circuit import DelaiCircuit
from app.models.parametre_officine import ParametreOfficine
from app.models.reference import Reference
from app.models.vente_mensuelle import VenteMensuelle
from app.services.moteur_sad import (
    appliquer_neutralisation_fsn,
    calc_classes_abc,
    calc_cmm,
    calc_cmmax,
    calc_couverture_jours,
    calc_eoq,
    calc_fsn,
    calc_niveau_recompletement,
    calc_pc,
    calc_qte_commander,
    calc_sigma,
    calc_ss,
    calc_ss_periodique,
    calc_statut,
    calc_tresorerie_liberee,
    get_z,
)


def _reset_ajustement_si_resolu(ref: Reference) -> None:
    """
    Un arbitrage manuel (section 6.7) n'a plus lieu d'être une fois le statut
    revenu à OK — sauf si le pharmacien a délibérément forcé l'inclusion,
    auquel cas son choix reste valable tant qu'il ne l'annule pas lui-même.
    """
    if ref.statut == "OK" and ref.inclusion_manuelle != "inclure":
        ref.qte_a_commander_override = None
        ref.inclusion_manuelle = None


def get_or_create_parametres(officine_id, db: Session) -> ParametreOfficine:
    """
    Retourne les paramètres de l'officine, en les créant avec les défauts si absent.

    Le tableau de bord déclenche plusieurs appels API en parallèle au
    chargement (kpis, commande-plafonnee...), qui peuvent chacun arriver ici
    avant qu'aucun n'ait encore créé la ligne : sans le try/except, le second
    flush() lève IntegrityError (officine_id est UNIQUE) au lieu de
    simplement récupérer la ligne que l'autre requête vient de créer.
    """
    params = db.query(ParametreOfficine).filter(
        ParametreOfficine.officine_id == officine_id
    ).first()
    if params is not None:
        return params

    params = ParametreOfficine(officine_id=officine_id)
    db.add(params)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        params = db.query(ParametreOfficine).filter(
            ParametreOfficine.officine_id == officine_id
        ).first()
    return params


def calculer_toutes_references(officine_id, db: Session) -> dict:
    """
    Lance le moteur SAD sur toutes les références d'une officine.
    Retourne un résumé {"nb_references": int, "nb_a_commander": int, "nb_rupture": int}.
    """
    params = get_or_create_parametres(officine_id, db)

    niveaux_service = {
        "Vital":     params.niveau_service_vital,
        "Essentiel": params.niveau_service_essentiel,
        "Désirable": params.niveau_service_desirable,
        None:        params.niveau_service_non_renseigne,
    }

    references = (
        db.query(Reference)
        .filter(Reference.officine_id == officine_id)
        .all()
    )
    if not references:
        return {"nb_references": 0, "nb_a_commander": 0, "nb_rupture": 0}

    # Délais fournisseurs par circuit (local/France/Chine-Inde...) — repli sur
    # le délai global de l'officine si le circuit de la référence n'est pas
    # renseigné ou n'a pas été configuré (section 5/8 du cahier des charges).
    delais_par_circuit = {
        d.circuit: (d.dl_moy_jours, d.dl_max_jours)
        for d in db.query(DelaiCircuit).filter(DelaiCircuit.officine_id == officine_id).all()
    }

    def delais_de(ref: Reference) -> tuple[int, int]:
        if ref.circuit and ref.circuit in delais_par_circuit:
            return delais_par_circuit[ref.circuit]
        return params.dl_moy_jours, params.dl_max_jours

    # Récupérer toutes les ventes en une seule requête
    ref_ids = [r.id for r in references]
    ventes_rows = (
        db.query(VenteMensuelle)
        .filter(VenteMensuelle.reference_id.in_(ref_ids))
        .all()
    )
    # Indexer par reference_id → liste ordonnée mois 1..12
    ventes_par_ref: dict = {}
    for v in ventes_rows:
        rid = str(v.reference_id)
        if rid not in ventes_par_ref:
            ventes_par_ref[rid] = {}
        ventes_par_ref[rid][v.mois_index] = v.quantite or 0.0

    # ── Étape 1 : calculs scalaires par référence ─────────────────────────────
    for ref in references:
        rid = str(ref.id)
        ventes_dict = ventes_par_ref.get(rid, {})
        ventes = [ventes_dict.get(i, 0.0) for i in range(1, 13)]

        cmm   = calc_cmm(ventes)
        cmmax = calc_cmmax(ventes)
        sigma = calc_sigma(ventes)
        fsn   = calc_fsn(ventes)
        z     = get_z(ref.ved, niveaux_service)
        dl_moy_jours, dl_max_jours = delais_de(ref)

        ss    = calc_ss(z, sigma, dl_max_jours)
        pc    = calc_pc(cmm, dl_moy_jours, ss)
        statut = calc_statut(ref.stock_actuel or 0.0, ss, pc)

        eoq   = calc_eoq(cmm, params.cout_commande, params.taux_detention, ref.prix_cession)

        Y     = ref.risque_fournisseur_jours or 0
        T     = params.cycle_commande_jours
        ss_p  = calc_ss_periodique(z, sigma, dl_max_jours, T, Y)
        S     = calc_niveau_recompletement(cmm, dl_moy_jours, T, Y, ss_p)
        qte_cycle = calc_qte_commander(S, ref.stock_actuel or 0.0)
        qte_cycle = appliquer_neutralisation_fsn(fsn, ref.ved, qte_cycle)

        couverture = calc_couverture_jours(ref.stock_actuel or 0.0, cmm)
        tresorerie = calc_tresorerie_liberee(ref.stock_actuel or 0.0, S, ref.prix_cession)

        # Persister sur l'objet (pas encore de flush individuel pour la perf)
        ref.cmm    = cmm
        ref.cmmax  = cmmax
        ref.sigma  = sigma
        ref.z_service = z
        ref.fsn    = fsn
        ref.ss     = ss
        ref.pc     = pc
        ref.statut = statut
        ref.eoq    = eoq
        ref.ss_periodique          = ss_p
        ref.niveau_recompletement  = S
        ref.qte_a_commander        = qte_cycle
        ref.couverture_jours       = couverture
        ref.tresorerie_liberee     = tresorerie
        _reset_ajustement_si_resolu(ref)

    # ── Étape 2 : classification ABC (nécessite tous les CMM) ─────────────────
    # CA = ventes 12 mois × Prix public (section 6.2) ; repli sur prix de
    # cession si le prix public est absent de l'import.
    abc_input = [
        {"id": str(r.id), "cmm": r.cmm, "prix_public": r.prix_public or r.prix_cession}
        for r in references
    ]
    classes = calc_classes_abc(abc_input)
    for ref in references:
        ref.classe = classes.get(str(ref.id), "C")

    db.flush()

    # ── Résumé ────────────────────────────────────────────────────────────────
    nb_a_commander = sum(
        1 for r in references if r.statut in ("RUPTURE", "CRITIQUE", "COMMANDER")
    )
    nb_rupture = sum(1 for r in references if r.statut == "RUPTURE")

    return {
        "nb_references": len(references),
        "nb_a_commander": nb_a_commander,
        "nb_rupture": nb_rupture,
    }


def recalculer_apres_commande(officine_id, db: Session) -> dict:
    """
    Recalcul léger après un import de commande (cycle décade/mensuel).

    Ne touche ni CMM/sigma/FSN/classe ABC ni SS/PC/EOQ/SS périodique/S : ces
    valeurs ne dépendent que de l'historique 12 mois et des réglages, pas du
    stock — elles restent celles du dernier import historique. Seul ce qui
    dépend du nouveau stock_actuel est rafraîchi : statut, quantités à
    commander, couverture et trésorerie libérée.
    """
    params = get_or_create_parametres(officine_id, db)

    references = (
        db.query(Reference)
        .filter(Reference.officine_id == officine_id)
        .all()
    )
    if not references:
        return {"nb_references": 0, "nb_a_commander": 0, "nb_rupture": 0}

    for ref in references:
        stock = ref.stock_actuel or 0.0

        ref.statut = calc_statut(stock, ref.ss or 0.0, ref.pc or 0.0)

        qte_cycle = calc_qte_commander(ref.niveau_recompletement or 0.0, stock)
        qte_cycle = appliquer_neutralisation_fsn(ref.fsn, ref.ved, qte_cycle)
        ref.qte_a_commander = qte_cycle

        ref.couverture_jours   = calc_couverture_jours(stock, ref.cmm or 0.0)
        ref.tresorerie_liberee = calc_tresorerie_liberee(
            stock, ref.niveau_recompletement or 0.0, ref.prix_cession
        )
        _reset_ajustement_si_resolu(ref)

    db.flush()

    nb_a_commander = sum(
        1 for r in references if r.statut in ("RUPTURE", "CRITIQUE", "COMMANDER")
    )
    nb_rupture = sum(1 for r in references if r.statut == "RUPTURE")

    return {
        "nb_references": len(references),
        "nb_a_commander": nb_a_commander,
        "nb_rupture": nb_rupture,
    }
