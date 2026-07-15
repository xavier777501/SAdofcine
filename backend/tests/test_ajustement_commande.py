"""
Section 6.7 du cahier des charges : "Le pharmacien garde toujours la main : il
peut ajuster manuellement les quantités, inclure ou exclure une référence."
Vérifie la route PATCH /references/{id}/ajustement-commande, sa répercussion
sur la liste d'action, et la remise à zéro automatique une fois le statut
redevenu OK (sauf inclusion volontaire, qui doit persister).
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import get_db, Base, engine
from app.core.security import get_password_hash
from app.models.officine import Officine
from app.models.user import User
from app.models.reference import Reference
from app.services.calcul_officine import recalculer_apres_commande


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
def ref_commander(db_session, officine):
    r = Reference(
        officine_id=officine.id,
        code="REF1",
        designation="Doliprane 500mg",
        statut="COMMANDER",
        classe="B",
        ved="Essentiel",
        fsn="Fast",
        qte_a_commander=10,
        prix_cession=1000,
        stock_actuel=5,
        cmm=5, ss=2, pc=10, niveau_recompletement=15,
    )
    db_session.add(r)
    db_session.commit()
    db_session.refresh(r)
    return r


class TestRouteAjustementCommande:
    def test_override_quantite(self, client, token, db_session, ref_commander):
        headers = {"Authorization": f"Bearer {token}"}
        response = client.patch(
            f"/api/v1/references/{ref_commander.id}/ajustement-commande",
            json={"qte_a_commander_override": 42},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["qte_a_commander_override"] == 42

        db_session.refresh(ref_commander)
        assert ref_commander.qte_a_commander_override == 42
        # La suggestion du moteur n'est pas écrasée, seule la surcouche l'est
        assert ref_commander.qte_a_commander == 10

    def test_exclusion_puis_reinclusion(self, client, token, db_session, ref_commander):
        headers = {"Authorization": f"Bearer {token}"}
        r1 = client.patch(
            f"/api/v1/references/{ref_commander.id}/ajustement-commande",
            json={"inclusion_manuelle": "exclure"},
            headers=headers,
        )
        assert r1.status_code == 200
        assert r1.json()["inclusion_manuelle"] == "exclure"

        liste = client.get("/api/v1/dashboard/liste-action", headers=headers).json()
        assert all(l["code"] != "REF1" for l in liste)

        r2 = client.patch(
            f"/api/v1/references/{ref_commander.id}/ajustement-commande",
            json={"inclusion_manuelle": None},
            headers=headers,
        )
        assert r2.status_code == 200
        liste = client.get("/api/v1/dashboard/liste-action", headers=headers).json()
        assert any(l["code"] == "REF1" for l in liste)

    def test_valeur_inclusion_manuelle_invalide_rejetee(self, client, token, ref_commander):
        headers = {"Authorization": f"Bearer {token}"}
        response = client.patch(
            f"/api/v1/references/{ref_commander.id}/ajustement-commande",
            json={"inclusion_manuelle": "peut-etre"},
            headers=headers,
        )
        assert response.status_code == 422

    def test_reference_introuvable(self, client, token):
        headers = {"Authorization": f"Bearer {token}"}
        response = client.patch(
            "/api/v1/references/00000000-0000-0000-0000-000000000000/ajustement-commande",
            json={"qte_a_commander_override": 5},
            headers=headers,
        )
        assert response.status_code == 404


class TestListeActionRespecteArbitrage:
    def test_override_visible_dans_liste_action(self, client, token, db_session, ref_commander):
        ref_commander.qte_a_commander_override = 99
        db_session.commit()

        headers = {"Authorization": f"Bearer {token}"}
        liste = client.get("/api/v1/dashboard/liste-action", headers=headers).json()
        ligne = next(l for l in liste if l["code"] == "REF1")
        assert ligne["qte_a_commander"] == 99
        assert ligne["qte_a_commander_auto"] == 10
        assert ligne["valeur_fcfa"] == 99000

    def test_inclusion_manuelle_fait_apparaitre_une_reference_ok(self, client, token, db_session, officine):
        r = Reference(
            officine_id=officine.id, code="OK1", designation="Vitamine C",
            statut="OK", classe="C", stock_actuel=50, prix_cession=500,
            inclusion_manuelle="inclure",
        )
        db_session.add(r)
        db_session.commit()

        headers = {"Authorization": f"Bearer {token}"}
        liste = client.get("/api/v1/dashboard/liste-action", headers=headers).json()
        ligne = next((l for l in liste if l["code"] == "OK1"), None)
        assert ligne is not None
        assert "manuellement" in ligne["texte_decision"]


class TestResetAutomatiqueSurStatutOk:
    def test_override_efface_quand_statut_redevient_ok(self, db_session, officine, ref_commander):
        ref_commander.qte_a_commander_override = 42
        ref_commander.stock_actuel = 100  # largement au-dessus du point de commande -> redevient OK
        db_session.commit()

        recalculer_apres_commande(officine.id, db_session)
        db_session.commit()
        db_session.refresh(ref_commander)

        assert ref_commander.statut == "OK"
        assert ref_commander.qte_a_commander_override is None
        assert ref_commander.inclusion_manuelle is None

    def test_inclusion_forcee_persiste_meme_si_statut_redevient_ok(self, db_session, officine, ref_commander):
        ref_commander.inclusion_manuelle = "inclure"
        ref_commander.stock_actuel = 100
        db_session.commit()

        recalculer_apres_commande(officine.id, db_session)
        db_session.commit()
        db_session.refresh(ref_commander)

        assert ref_commander.statut == "OK"
        assert ref_commander.inclusion_manuelle == "inclure"
