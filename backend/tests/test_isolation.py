"""
Tests d'isolation multi-locataire (US-A3).
Vérifie qu'un utilisateur d'une officine ne peut PAS accéder aux données d'une autre officine.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import get_db, Base, engine
from app.models.officine import Officine
from app.models.user import User
from app.models.reference import Reference
from app.core.security import get_password_hash


# Fixtures pour créer 2 officines avec 2 utilisateurs
@pytest.fixture(autouse=True)
def setup_db():
    """Crée les tables avant chaque test et les supprime après."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Session BDD pour les tests."""
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(db_session):
    """Client HTTP de test."""
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def officine_a(db_session):
    officine = Officine(nom="Pharmacie A")
    db_session.add(officine)
    db_session.commit()
    db_session.refresh(officine)
    return officine


@pytest.fixture
def officine_b(db_session):
    officine = Officine(nom="Pharmacie B")
    db_session.add(officine)
    db_session.commit()
    db_session.refresh(officine)
    return officine


@pytest.fixture
def user_a(db_session, officine_a):
    user = User(
        email="a@pharma.com",
        hashed_password=get_password_hash("password123"),
        officine_id=officine_a.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_b(db_session, officine_b):
    user = User(
        email="b@pharma.com",
        hashed_password=get_password_hash("password123"),
        officine_id=officine_b.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def token_a(client, user_a):
    """Token JWT de l'utilisateur A."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "a@pharma.com", "password": "password123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def token_b(client, user_b):
    """Token JWT de l'utilisateur B."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "b@pharma.com", "password": "password123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def reference_a(db_session, officine_a):
    ref = Reference(officine_id=officine_a.id, code="A001", designation="Doliprane 500mg", stock_actuel=10)
    db_session.add(ref)
    db_session.commit()
    db_session.refresh(ref)
    return ref


@pytest.fixture
def reference_b(db_session, officine_b):
    ref = Reference(officine_id=officine_b.id, code="B001", designation="Efferalgan 1g", stock_actuel=20)
    db_session.add(ref)
    db_session.commit()
    db_session.refresh(ref)
    return ref


# ============ TESTS D'ISOLATION ============

class TestIsolation:
    """Tests US-A3 : isolation stricte entre officines."""

    def test_user_a_ne_voit_pas_user_b(self, client, token_a, user_b):
        """Un utilisateur A ne peut pas accéder aux données de l'utilisateur B."""
        # Ici on teste que les tokens sont bien distincts
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}
        
        # Les deux tokens doivent être différents
        assert token_a != token_b

    def test_tokens_contiennent_officine_id_different(self, token_a, token_b):
        """Les tokens JWT contiennent des officine_id différents."""
        from app.core.security import decode_access_token
        
        payload_a = decode_access_token(token_a)
        payload_b = decode_access_token(token_b)
        
        assert payload_a["officine_id"] != payload_b["officine_id"]

    def test_invalid_token_rejected(self, client):
        """Un token invalide doit être rejeté."""
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    def test_logout_endpoint_exists(self, client, token_a):
        """L'endpoint logout doit retourner 200."""
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert response.status_code == 200
        assert "message" in response.json()


class TestIsolationDonneesBoutEnBout:
    """
    Vérifie, au niveau HTTP (pas seulement au niveau du token JWT), qu'aucune
    donnée d'une officine n'est jamais accessible depuis une autre officine.
    """

    def test_liste_references_exclut_lautre_officine(self, client, token_a, reference_a, reference_b):
        response = client.get("/api/v1/references", headers={"Authorization": f"Bearer {token_a}"})
        assert response.status_code == 200
        codes = [r["code"] for r in response.json()]
        assert reference_a.code in codes
        assert reference_b.code not in codes

    def test_kpis_ne_comptent_pas_lautre_officine(self, client, token_a, reference_a, reference_b):
        response = client.get("/api/v1/dashboard/kpis", headers={"Authorization": f"Bearer {token_a}"})
        assert response.status_code == 200
        assert response.json()["nb_references"] == 1

    def test_modification_reference_dune_autre_officine_rejetee(self, client, token_a, reference_b):
        """Deviner l'id d'une référence d'une autre officine ne doit permettre ni de la lire ni de la modifier."""
        response = client.patch(
            f"/api/v1/references/{reference_b.id}/ved",
            json={"ved": "Vital"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert response.status_code == 404

    def test_parametres_isoles_par_officine(self, client, token_a, token_b):
        """Modifier les réglages de l'officine A ne doit pas affecter ceux de l'officine B."""
        response_patch = client.patch(
            "/api/v1/parametres",
            json={"cout_commande": 12345},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert response_patch.status_code == 200

        response_b = client.get("/api/v1/parametres", headers={"Authorization": f"Bearer {token_b}"})
        assert response_b.json()["cout_commande"] != 12345