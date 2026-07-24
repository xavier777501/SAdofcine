"""
Section 6.8 du cahier des charges V9 : gestion de la rupture fournisseur.
Une référence mise en attente jusqu'à une date de réévaluation disparaît de
la liste d'action, du plafond budgétaire et de l'encart 7.0 — sauf exception
absolue : une référence RUPTURE + Vital reste toujours visible partout.
"""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import get_db, Base, engine
from app.core.security import get_password_hash
from app.models.officine import Officine
from app.models.user import User
from app.models.reference import Reference
from app.services.rupture_fournisseur import doit_etre_masquee, en_attente_fournisseur


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


def _ref(officine_id, code, statut, ved=None, classe="A", fsn="Fast", qte=10, prix=1000,
         en_attente_jusqu_au=None, inclusion=None):
    return Reference(
        officine_id=officine_id,
        code=code,
        designation=f"Produit {code}",
        statut=statut,
        ved=ved,
        classe=classe,
        fsn=fsn,
        qte_a_commander=qte,
        prix_cession=prix,
        prix_public=prix,
        stock_actuel=5,
        fournisseur_indisponible_jusqu_au=en_attente_jusqu_au,
        inclusion_manuelle=inclusion,
    )


class TestHelperEnAttente:
    def test_en_attente_si_date_future(self, officine):
        ref = _ref(officine.id, "A", "CRITIQUE", en_attente_jusqu_au=date.today() + timedelta(days=5))
        assert en_attente_fournisseur(ref) is True

    def test_pas_en_attente_si_date_passee(self, officine):
        ref = _ref(officine.id, "A", "CRITIQUE", en_attente_jusqu_au=date.today() - timedelta(days=1))
        assert en_attente_fournisseur(ref) is False

    def test_pas_en_attente_si_aucune_date(self, officine):
        ref = _ref(officine.id, "A", "CRITIQUE")
        assert en_attente_fournisseur(ref) is False

    def test_rupture_vital_jamais_masquee_meme_en_attente(self, officine):
        ref = _ref(officine.id, "A", "RUPTURE", ved="Vital", en_attente_jusqu_au=date.today() + timedelta(days=5))
        assert en_attente_fournisseur(ref) is True
        assert doit_etre_masquee(ref) is False

    def test_critique_vital_en_attente_est_masquee(self, officine):
        # L'exception ne couvre que RUPTURE + Vital, pas CRITIQUE + Vital.
        ref = _ref(officine.id, "A", "CRITIQUE", ved="Vital", en_attente_jusqu_au=date.today() + timedelta(days=5))
        assert doit_etre_masquee(ref) is True

    def test_inclusion_manuelle_bypasse_la_mise_en_attente(self, officine):
        ref = _ref(officine.id, "A", "CRITIQUE", en_attente_jusqu_au=date.today() + timedelta(days=5), inclusion="inclure")
        assert doit_etre_masquee(ref) is False


class TestIntegrationListeActionEtAlertes:
    def test_reference_en_attente_disparait_de_la_liste_daction(self, client, token, db_session, officine):
        headers = {"Authorization": f"Bearer {token}"}
        db_session.add(_ref(officine.id, "A", "CRITIQUE", en_attente_jusqu_au=date.today() + timedelta(days=5)))
        db_session.add(_ref(officine.id, "B", "CRITIQUE"))
        db_session.commit()

        liste = client.get("/api/v1/dashboard/liste-action", headers=headers).json()
        codes = [l["code"] for l in liste]
        assert "A" not in codes
        assert "B" in codes

    def test_reference_en_attente_reapparait_apres_la_date(self, client, token, db_session, officine):
        headers = {"Authorization": f"Bearer {token}"}
        db_session.add(_ref(officine.id, "A", "CRITIQUE", en_attente_jusqu_au=date.today() - timedelta(days=1)))
        db_session.commit()

        liste = client.get("/api/v1/dashboard/liste-action", headers=headers).json()
        assert "A" in [l["code"] for l in liste]

    def test_rupture_vital_en_attente_reste_dans_la_liste_et_les_alertes(self, client, token, db_session, officine):
        headers = {"Authorization": f"Bearer {token}"}
        db_session.add(_ref(
            officine.id, "A", "RUPTURE", ved="Vital", classe="A",
            en_attente_jusqu_au=date.today() + timedelta(days=5),
        ))
        db_session.commit()

        liste = client.get("/api/v1/dashboard/liste-action", headers=headers).json()
        assert "A" in [l["code"] for l in liste]

        plafond = client.get("/api/v1/dashboard/commande-plafonnee", headers=headers).json()
        assert "A" in [l["code"] for l in plafond["hors_plafond"]]

    def test_reference_en_attente_absente_de_lencart_alertes_strategiques(self, client, token, db_session, officine):
        headers = {"Authorization": f"Bearer {token}"}
        db_session.add(_ref(
            officine.id, "A", "CRITIQUE", classe="A",
            en_attente_jusqu_au=date.today() + timedelta(days=5),
        ))
        db_session.commit()

        alertes = client.get("/api/v1/dashboard/alertes-strategiques", headers=headers).json()
        assert alertes["nb_references"] == 0

    def test_endpoint_en_attente_fournisseur_retourne_la_reference(self, client, token, db_session, officine):
        headers = {"Authorization": f"Bearer {token}"}
        db_session.add(_ref(officine.id, "A", "CRITIQUE", en_attente_jusqu_au=date.today() + timedelta(days=5)))
        db_session.add(_ref(officine.id, "B", "CRITIQUE"))
        db_session.commit()

        response = client.get("/api/v1/dashboard/en-attente-fournisseur", headers=headers)
        assert response.status_code == 200
        codes = [l["code"] for l in response.json()]
        assert codes == ["A"]


class TestEndpointPatch:
    def test_mise_en_attente_puis_reactivation(self, client, token, db_session, officine):
        headers = {"Authorization": f"Bearer {token}"}
        ref = _ref(officine.id, "A", "CRITIQUE")
        db_session.add(ref)
        db_session.commit()
        db_session.refresh(ref)

        date_reeval = (date.today() + timedelta(days=10)).isoformat()
        response = client.patch(
            f"/api/v1/references/{ref.id}/fournisseur-indisponible",
            json={"date_reevaluation": date_reeval},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["fournisseur_indisponible_jusqu_au"] == date_reeval

        # Disparaît bien de la liste d'action une fois posée
        liste = client.get("/api/v1/dashboard/liste-action", headers=headers).json()
        assert "A" not in [l["code"] for l in liste]

        # Réactivation manuelle (date_reevaluation=None)
        response2 = client.patch(
            f"/api/v1/references/{ref.id}/fournisseur-indisponible",
            json={"date_reevaluation": None},
            headers=headers,
        )
        assert response2.status_code == 200
        assert response2.json()["fournisseur_indisponible_jusqu_au"] is None

        liste2 = client.get("/api/v1/dashboard/liste-action", headers=headers).json()
        assert "A" in [l["code"] for l in liste2]
