"""
Orchestration du calcul SAD pour une officine complète.
Récupère les données en BDD, appelle les fonctions pures de moteur_sad,
et persiste les résultats sur chaque référence.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

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
    calc_qte_commander_continu,
    calc_sigma,
    calc_ss,
    calc_ss_periodique,
    calc_statut,
    calc_tresorerie_liberee,
    get_z,
)


def get_or_create_parametres(officine_id, db: Session) -> ParametreOfficine:
    """Retourne les paramètres de l'officine, en les créant avec les défauts si absent."""
    params = db.query(ParametreOfficine).filter(
        ParametreOfficine.officine_id == officine_id
    ).first()
    if params is None:
        params = ParametreOfficine(officine_id=officine_id)
        db.add(params)
        db.flush()
    return params


def calculer_toutes_references(officine_id, db: Session) -> dict:
    """
    Lance le moteur SAD sur toutes les références d'une officine.
    Retourne un résumé {"nb_references": int, "nb_a_commander": int, "nb_rupture": int}.
    """
    params = get_or_create_parametres(officine_id, db)

    references = (
        db.query(Reference)
        .filter(Reference.officine_id == officine_id)
        .all()
    )
    if not references:
        return {"nb_references": 0, "nb_a_commander": 0, "nb_rupture": 0}

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
        z     = get_z(ref.ved)

        ss    = calc_ss(z, sigma, params.dl_max_jours)
        pc    = calc_pc(cmm, params.dl_moy_jours, ss)
        statut = calc_statut(ref.stock_actuel or 0.0, ss, pc)

        eoq   = calc_eoq(cmm, params.cout_commande, params.taux_detention, ref.prix_cession)

        Y     = ref.risque_fournisseur_jours or 0
        T     = params.cycle_commande_jours
        ss_p  = calc_ss_periodique(z, sigma, params.dl_max_jours, T, Y)
        S     = calc_niveau_recompletement(cmm, params.dl_moy_jours, T, Y, ss_p)
        qte_cycle   = calc_qte_commander(S, ref.stock_actuel or 0.0)
        qte_continu = calc_qte_commander_continu(pc, ref.stock_actuel or 0.0, cmm)

        qte_cycle, qte_continu = appliquer_neutralisation_fsn(
            fsn, ref.ved, qte_cycle, qte_continu
        )

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
        ref.qte_commander_continu  = qte_continu
        ref.couverture_jours       = couverture
        ref.tresorerie_liberee     = tresorerie

    # ── Étape 2 : classification ABC (nécessite tous les CMM) ─────────────────
    abc_input = [
        {"id": str(r.id), "cmm": r.cmm, "prix_cession": r.prix_cession}
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
