"""
Section 6.5 du cahier des charges : la formule périodique (SS_periodique, S,
Qte_a_commander) est générique en T (intervalle en jours entre deux
commandes) — 1 (journalière), 10 (décade) et 30 (mensuel) sont les rythmes
usuels proposés, pas des cas particuliers câblés en dur dans la formule.
Vérifie que le réglage accepte ces trois valeurs et rejette les autres, et
que le moteur recalcule bien avec le nouveau T.
"""
import math

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import get_db, Base, engine
from app.core.security import get_password_hash
from app.models.officine import Officine
from app.models.user import User
from app.models.reference import Reference
from app.models.vente_mensuelle import VenteMensuelle


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def officine(db_session):
    o = Officine(nom="Pharmacie Test")
    db_session.add(o)
    db_session.commit()
    db_session.refresh(o)
    return o


@pytest.fixture
def user(db_session, officine):
    u = User(
        email="pharma@test.com",
        hashed_password=get_password_hash("password123"),
        officine_id=officine.id,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def token(client, user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "pharma@test.com", "password": "password123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def ref_calculee(db_session, officine):
    """Référence classe A avec 12 mois de ventes régulières, pour un sigma > 0."""
    r = Reference(
        officine_id=officine.id,
        code="A001",
        designation="Doliprane 500mg",
        prix_cession=500.0,
        prix_public=800.0,
        stock_actuel=50.0,
        ved="Vital",
    )
    db_session.add(r)
    db_session.commit()
    db_session.refresh(r)

    ventes = [100, 110, 90, 105, 95, 100, 120, 80, 100, 100, 90, 110]
    for i, qte in enumerate(ventes, start=1):
        db_session.add(VenteMensuelle(reference_id=r.id, mois_index=i, quantite=qte))
    db_session.commit()
    return r


class TestCycleCommandeAccepteLesTroisRythmes:
    @pytest.mark.parametrize("cycle", [1, 10, 30])
    def test_valeur_acceptee(self, client, token, cycle):
        headers = {"Authorization": f"Bearer {token}"}
        response = client.patch(
            "/api/v1/parametres", json={"cycle_commande_jours": cycle}, headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["cycle_commande_jours"] == cycle

    @pytest.mark.parametrize("cycle", [0, 5, 15, 20, 60])
    def test_valeur_hors_liste_rejetee(self, client, token, cycle):
        headers = {"Authorization": f"Bearer {token}"}
        response = client.patch(
            "/api/v1/parametres", json={"cycle_commande_jours": cycle}, headers=headers,
        )
        assert response.status_code == 422


class TestFormulePeriodiqueGeneriqueEnT:
    """
    Vérifie que passer de T=10 à T=1 recalcule S et Qte_a_commander avec
    exactement la même formule (6.5), juste un T différent — pas une logique
    séparée ni une approximation.
    """

    def test_recalcul_coherent_avec_la_formule_pour_t_egal_1(self, client, token, db_session, ref_calculee):
        headers = {"Authorization": f"Bearer {token}"}
        response = client.patch(
            "/api/v1/parametres",
            json={"cycle_commande_jours": 1, "dl_moy_jours": 7, "dl_max_jours": 15},
            headers=headers,
        )
        assert response.status_code == 200

        db_session.refresh(ref_calculee)
        ref = ref_calculee
        assert ref.cmm is not None and ref.sigma is not None and ref.z_service is not None

        T, Y = 1, ref.risque_fournisseur_jours or 0
        attendu_ss_p = max(0.0, ref.z_service * ref.sigma * math.sqrt((15 + T + Y) / 30.0))
        attendu_s = (ref.cmm / 30.0) * (7 + T + Y) + attendu_ss_p
        attendu_qte = max(0.0, math.floor(attendu_s - ref.stock_actuel + 0.5))

        assert ref.ss_periodique == pytest.approx(attendu_ss_p, rel=1e-6)
        assert ref.niveau_recompletement == pytest.approx(attendu_s, rel=1e-6)
        assert ref.qte_a_commander == pytest.approx(attendu_qte, rel=1e-6)

    def test_journalier_donne_un_recompletement_plus_bas_que_mensuel(self, client, token, db_session, ref_calculee):
        """
        Plus le cycle est court, moins il faut couvrir de jours entre deux
        commandes -> S (niveau de recomplètement) doit diminuer avec T,
        toutes choses égales par ailleurs (formule 6.5, terme (DLmoy+T+Y)).
        """
        headers = {"Authorization": f"Bearer {token}"}

        client.patch("/api/v1/parametres", json={"cycle_commande_jours": 30}, headers=headers)
        db_session.refresh(ref_calculee)
        s_mensuel = ref_calculee.niveau_recompletement

        client.patch("/api/v1/parametres", json={"cycle_commande_jours": 1}, headers=headers)
        db_session.refresh(ref_calculee)
        s_journalier = ref_calculee.niveau_recompletement

        assert s_journalier < s_mensuel
