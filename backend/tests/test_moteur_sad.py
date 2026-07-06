"""
US-G1 — Tests de non-régression du moteur SAD.

Cas de test basés sur des références réelles extraites du fichier
SAD_OFFICINE_REFERENCE_DEVELOPPEUR.xlsx (onglet MODÈLE SAD).
Tolérance numérique : 0.01 sur tous les résultats calculés.

Convention sur les fixtures :
  ventes[0] = mois_index 1 (mois le plus récent, M-1)
  ventes[11] = mois_index 12 (le plus ancien, M-12)
"""
import math
import pytest

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

TOL = 0.01  # tolérance absolue pour les comparaisons numériques


def approx(a: float, b: float) -> bool:
    return abs(a - b) <= TOL


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures — ventes mensuelles (mois 1 = le plus récent)
# ─────────────────────────────────────────────────────────────────────────────

# Référence A — produit Fast, ventes régulières ~15/mois
VENTES_A = [15.0, 14.0, 16.0, 15.0, 13.0, 17.0, 14.0, 15.0, 16.0, 14.0, 15.0, 16.0]

# Référence B — produit Slow, ventes irrégulières
VENTES_B = [0.0, 3.0, 0.0, 2.0, 0.0, 1.0, 0.0, 2.0, 0.0, 0.0, 1.0, 0.0]

# Référence C — produit Non-moving, 1 seul mois de vente
VENTES_C = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.0, 0.0, 0.0]

# Référence D — produit avec pic (CMMax >> CMM)
VENTES_D = [2.0, 1.0, 3.0, 1.0, 2.0, 1.0, 50.0, 2.0, 1.0, 2.0, 1.0, 2.0]

# Référence E — produit avec ventes nulles (rupture fournisseur)
VENTES_E = [0.0] * 12

# Référence F — ventes croissantes
VENTES_F = [20.0, 18.0, 16.0, 14.0, 12.0, 10.0, 8.0, 6.0, 4.0, 2.0, 1.0, 1.0]

# Référence G — produit à fort volume
VENTES_G = [100.0, 98.0, 102.0, 99.0, 101.0, 100.0, 97.0, 103.0, 100.0, 99.0, 101.0, 100.0]

# Référence H — Slow avec quelques ventes
VENTES_H = [5.0, 0.0, 0.0, 4.0, 0.0, 0.0, 3.0, 0.0, 0.0, 0.0, 0.0, 0.0]

# Référence I — Fast, ventes légèrement variables
VENTES_I = [30.0, 28.0, 32.0, 29.0, 31.0, 30.0, 28.0, 33.0, 30.0, 29.0, 31.0, 30.0]

# Référence J — ventes décroissantes (produit en perte de vitesse)
VENTES_J = [1.0, 2.0, 2.0, 3.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]


# ─────────────────────────────────────────────────────────────────────────────
# US-D1 : CMM et CMMax
# ─────────────────────────────────────────────────────────────────────────────

class TestCMM:
    def test_ref_a_reguliere(self):
        cmm = calc_cmm(VENTES_A)
        assert approx(cmm, sum(VENTES_A) / 12)

    def test_ref_b_irreguliere(self):
        cmm = calc_cmm(VENTES_B)
        assert approx(cmm, sum(VENTES_B) / 12)  # = 9/12 = 0.75

    def test_ref_e_zero(self):
        assert calc_cmm(VENTES_E) == 0.0

    def test_negatifs_exclus(self):
        ventes_neg = [-5.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
        # le -5 devient 0 dans le calcul
        assert approx(calc_cmm(ventes_neg), (0 + 10 * 11) / 12)

    def test_ref_g_fort_volume(self):
        cmm = calc_cmm(VENTES_G)
        assert approx(cmm, sum(VENTES_G) / 12)

    def test_liste_vide(self):
        assert calc_cmm([]) == 0.0


class TestCMMax:
    def test_ref_a(self):
        assert calc_cmmax(VENTES_A) == 17.0

    def test_ref_d_pic(self):
        assert calc_cmmax(VENTES_D) == 50.0

    def test_ref_e_zero(self):
        assert calc_cmmax(VENTES_E) == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# US-D3 : Écart-type σ
# ─────────────────────────────────────────────────────────────────────────────

class TestSigma:
    def test_ref_a_faible_variabilite(self):
        sigma = calc_sigma(VENTES_A)
        # Ventes proches de 15, écart-type doit être < 2
        assert sigma < 2.0
        assert sigma > 0.0

    def test_ref_d_forte_variabilite(self):
        sigma_d = calc_sigma(VENTES_D)
        sigma_a = calc_sigma(VENTES_A)
        # Ref D a un pic à 50, donc bien plus variable
        assert sigma_d > sigma_a * 5

    def test_ref_e_zero(self):
        assert calc_sigma(VENTES_E) == 0.0

    def test_valeur_connue(self):
        # 4 valeurs simples : [2, 4, 4, 4, 5, 5, 7, 9] → σ = 2.0 (population)
        # mais on a 12 valeurs, utilisons un cas simple :
        ventes = [10.0] * 12  # pas de variabilité
        assert calc_sigma(ventes) == 0.0

    def test_ref_g_faible_variabilite(self):
        sigma = calc_sigma(VENTES_G)
        assert sigma < 3.0  # ventes autour de 100, peu variables


# ─────────────────────────────────────────────────────────────────────────────
# US-D7 : Classification FSN
# ─────────────────────────────────────────────────────────────────────────────

class TestFSN:
    def test_fast_12_mois(self):
        assert calc_fsn(VENTES_A) == "Fast"  # 12 mois > 0

    def test_fast_10_mois(self):
        ventes = [0.0, 0.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0]  # 10 mois
        assert calc_fsn(ventes) == "Fast"

    def test_slow_ref_b(self):
        assert calc_fsn(VENTES_B) == "Slow"  # 5 mois actifs

    def test_slow_ref_h(self):
        assert calc_fsn(VENTES_H) == "Slow"  # 3 mois actifs

    def test_non_moving_ref_c(self):
        assert calc_fsn(VENTES_C) == "Non-moving"  # 1 seul mois

    def test_non_moving_zero(self):
        assert calc_fsn(VENTES_E) == "Non-moving"  # 0 mois

    def test_frontiere_slow_9_mois(self):
        ventes = [5.0] * 9 + [0.0] * 3
        assert calc_fsn(ventes) == "Slow"

    def test_frontiere_non_moving_2_mois(self):
        ventes = [5.0, 5.0] + [0.0] * 10
        assert calc_fsn(ventes) == "Non-moving"


# ─────────────────────────────────────────────────────────────────────────────
# Facteur Z selon VED
# ─────────────────────────────────────────────────────────────────────────────

class TestGetZ:
    def test_vital(self):
        assert get_z("Vital") == 2.33

    def test_essentiel(self):
        assert get_z("Essentiel") == 1.645

    def test_desirable(self):
        assert get_z("Désirable") == 1.28

    def test_non_renseigne_none(self):
        assert get_z(None) == 1.645

    def test_non_renseigne_inconnu(self):
        assert get_z("autre") == 1.645


# ─────────────────────────────────────────────────────────────────────────────
# US-D4 : SS continu, PC, statut
# ─────────────────────────────────────────────────────────────────────────────

class TestSSContinu:
    def test_formule_de_base(self):
        z, sigma, dl_max = 1.645, 2.0, 15
        ss = calc_ss(z, sigma, dl_max)
        expected = z * sigma * math.sqrt(dl_max / 30.0)
        assert approx(ss, expected)

    def test_sigma_zero_donne_ss_zero(self):
        assert calc_ss(1.645, 0.0, 15) == 0.0

    def test_dl_max_zero_donne_ss_zero(self):
        assert calc_ss(1.645, 2.0, 0) == 0.0

    def test_ref_a_avec_params_standards(self):
        sigma = calc_sigma(VENTES_A)
        ss = calc_ss(1.645, sigma, 15)
        assert ss >= 0.0

    def test_vital_plus_grand_que_desirable(self):
        sigma = calc_sigma(VENTES_I)
        ss_vital     = calc_ss(get_z("Vital"),     sigma, 15)
        ss_desirable = calc_ss(get_z("Désirable"), sigma, 15)
        assert ss_vital > ss_desirable


class TestPC:
    def test_formule_de_base(self):
        cmm, dl_moy, ss = 15.0, 7, 3.0
        pc = calc_pc(cmm, dl_moy, ss)
        expected = (cmm / 30.0) * dl_moy + ss
        assert approx(pc, expected)

    def test_pc_superieur_a_ss(self):
        sigma = calc_sigma(VENTES_A)
        cmm   = calc_cmm(VENTES_A)
        ss    = calc_ss(1.645, sigma, 15)
        pc    = calc_pc(cmm, 7, ss)
        assert pc >= ss

    def test_cmm_zero(self):
        assert approx(calc_pc(0.0, 7, 2.0), 2.0)  # PC = SS quand CMM=0


class TestStatut:
    def test_rupture(self):
        assert calc_statut(0.0, 5.0, 15.0) == "RUPTURE"

    def test_rupture_negatif(self):
        assert calc_statut(-1.0, 5.0, 15.0) == "RUPTURE"

    def test_critique(self):
        assert calc_statut(3.0, 5.0, 15.0) == "CRITIQUE"

    def test_commander(self):
        assert calc_statut(10.0, 5.0, 15.0) == "COMMANDER"

    def test_ok(self):
        assert calc_statut(20.0, 5.0, 15.0) == "OK"

    def test_exactement_ss_est_critique(self):
        assert calc_statut(5.0, 5.0, 15.0) == "CRITIQUE"

    def test_exactement_pc_est_commander(self):
        assert calc_statut(15.0, 5.0, 15.0) == "COMMANDER"


# ─────────────────────────────────────────────────────────────────────────────
# US-D5 : EOQ
# ─────────────────────────────────────────────────────────────────────────────

class TestEOQ:
    def test_formule_wilson(self):
        cmm, cout_cmd, taux, prix = 15.0, 5000.0, 0.20, 1000.0
        eoq = calc_eoq(cmm, cout_cmd, taux, prix)
        expected = math.sqrt(2 * 15 * 12 * 5000 / (0.20 * 1000))
        assert approx(eoq, expected)

    def test_prix_zero_retourne_none(self):
        assert calc_eoq(15.0, 5000.0, 0.20, 0.0) is None

    def test_prix_none_retourne_none(self):
        assert calc_eoq(15.0, 5000.0, 0.20, None) is None

    def test_cmm_zero_retourne_none(self):
        assert calc_eoq(0.0, 5000.0, 0.20, 1000.0) is None

    def test_positif(self):
        eoq = calc_eoq(15.0, 5000.0, 0.20, 1000.0)
        assert eoq > 0


# ─────────────────────────────────────────────────────────────────────────────
# US-D6 : Cycle périodique
# ─────────────────────────────────────────────────────────────────────────────

class TestCyclePeriodique:
    def test_ss_periodique_superieur_ss_continu(self):
        # Avec T > 0, SS périodique doit être > SS continu
        sigma = calc_sigma(VENTES_A)
        z = 1.645
        ss_c = calc_ss(z, sigma, 15)
        ss_p = calc_ss_periodique(z, sigma, 15, T=10, Y=0)
        assert ss_p > ss_c

    def test_ss_periodique_formule(self):
        z, sigma, dl_max, T, Y = 1.645, 2.0, 15, 10, 3
        ss_p = calc_ss_periodique(z, sigma, dl_max, T, Y)
        expected = z * sigma * math.sqrt((dl_max + T + Y) / 30.0)
        assert approx(ss_p, expected)

    def test_niveau_recompletement_formule(self):
        cmm, dl_moy, T, Y, ss_p = 15.0, 7, 10, 0, 3.0
        S = calc_niveau_recompletement(cmm, dl_moy, T, Y, ss_p)
        expected = (cmm / 30.0) * (dl_moy + T + Y) + ss_p
        assert approx(S, expected)

    def test_qte_commander_positive(self):
        S, stock = 30.0, 10.0
        assert calc_qte_commander(S, stock) == 20.0

    def test_qte_commander_zero_si_stock_suffisant(self):
        assert calc_qte_commander(20.0, 25.0) == 0.0

    def test_qte_commander_arrondie(self):
        assert calc_qte_commander(30.5, 10.0) == 21.0  # ROUND(20.5, 0) = 21

    def test_risque_fournisseur_augmente_ss(self):
        sigma = calc_sigma(VENTES_I)
        z = 1.645
        ss_sans_risque = calc_ss_periodique(z, sigma, 15, T=10, Y=0)
        ss_avec_risque = calc_ss_periodique(z, sigma, 15, T=10, Y=7)
        assert ss_avec_risque > ss_sans_risque


# ─────────────────────────────────────────────────────────────────────────────
# US-D8 : Neutralisation Non-moving
# ─────────────────────────────────────────────────────────────────────────────

class TestNeutralisationFSN:
    def test_non_moving_standard_neutralise(self):
        q_p, q_c = appliquer_neutralisation_fsn("Non-moving", None, 5.0, 3.0)
        assert q_p == 0.0
        assert q_c == 0.0

    def test_non_moving_vital_donne_un(self):
        q_p, q_c = appliquer_neutralisation_fsn("Non-moving", "Vital", 5.0, 3.0)
        assert q_p == 1.0
        assert q_c == 1.0

    def test_fast_non_neutralise(self):
        q_p, q_c = appliquer_neutralisation_fsn("Fast", None, 5.0, 3.0)
        assert q_p == 5.0
        assert q_c == 3.0

    def test_slow_non_neutralise(self):
        q_p, q_c = appliquer_neutralisation_fsn("Slow", "Essentiel", 4.0, 2.0)
        assert q_p == 4.0
        assert q_c == 2.0


# ─────────────────────────────────────────────────────────────────────────────
# US-D2 : Classification ABC
# ─────────────────────────────────────────────────────────────────────────────

class TestABC:
    def _build_refs(self, data):
        return [{"id": k, "cmm": v["cmm"], "prix_cession": v["prix"]} for k, v in data.items()]

    def test_repartition_classique(self):
        # 1 produit domine le CA → classe A ; les petits → C
        data = {
            "r1": {"cmm": 100.0, "prix": 1000.0},   # CA = 1 200 000
            "r2": {"cmm": 1.0,   "prix": 10.0},     # CA = 120
            "r3": {"cmm": 0.5,   "prix": 10.0},     # CA = 60
        }
        refs = self._build_refs(data)
        classes = calc_classes_abc(refs)
        assert classes["r1"] == "A"
        assert classes["r2"] in ("B", "C")
        assert classes["r3"] == "C"

    def test_ca_zero_tout_c(self):
        refs = [
            {"id": "r1", "cmm": 0.0, "prix_cession": 0.0},
            {"id": "r2", "cmm": 0.0, "prix_cession": None},
        ]
        classes = calc_classes_abc(refs)
        assert all(v == "C" for v in classes.values())

    def test_aucune_ref_vide(self):
        assert calc_classes_abc([]) == {}

    def test_seuils_80_95(self):
        # 3 groupes bien séparés : A domine, B intermédiaire, C marginal
        # total CA = 8000 + 1500 + 500 = 10000
        # r1 seul = 80% → A (cumul_avant=0% < 80%)
        # r2..r4 = 15% → B (cumul_avant entre 80% et 95%)
        # r5..r10 = 5% → C (cumul_avant ≥ 95%)
        refs = [
            {"id": "r1", "cmm": 666.67, "prix_cession": 1.0},  # CA≈8000
            {"id": "r2", "cmm": 166.67, "prix_cession": 0.5},  # CA≈1000 (x3=3000 → 80-95%)
            {"id": "r3", "cmm": 166.67, "prix_cession": 0.5},
            {"id": "r4", "cmm": 100.0,  "prix_cession": 0.4},  # CA≈480
            {"id": "r5", "cmm": 10.0,   "prix_cession": 0.1},  # CA≈12 (x3=36 → >95%)
            {"id": "r6", "cmm": 10.0,   "prix_cession": 0.1},
        ]
        classes = calc_classes_abc(refs)
        # Le premier article (dominant) est en A
        assert classes["r1"] == "A"
        # Les derniers articles (marginaux) sont en C
        assert classes["r5"] == "C"
        assert classes["r6"] == "C"


# ─────────────────────────────────────────────────────────────────────────────
# Couverture jours et trésorerie libérée
# ─────────────────────────────────────────────────────────────────────────────

class TestIndicateursSupplementaires:
    def test_couverture_formule(self):
        stock, cmm = 30.0, 15.0
        couv = calc_couverture_jours(stock, cmm)
        assert approx(couv, (30.0 / 15.0) * 30.0)  # = 60 jours

    def test_couverture_cmm_zero(self):
        assert calc_couverture_jours(10.0, 0.0) is None

    def test_tresorerie_liberee_exces(self):
        stock, S, prix = 100.0, 30.0, 500.0
        treso = calc_tresorerie_liberee(stock, S, prix)
        assert approx(treso, (100.0 - 30.0) * 500.0)

    def test_tresorerie_sans_exces(self):
        # Stock inférieur au niveau de recomplètement → trésorerie = 0
        assert calc_tresorerie_liberee(10.0, 30.0, 500.0) == 0.0

    def test_tresorerie_prix_none(self):
        assert calc_tresorerie_liberee(100.0, 30.0, None) == 0.0
