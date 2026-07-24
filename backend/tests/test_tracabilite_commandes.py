"""
Section 7.3 du cahier des charges V9 : traçabilité des commandes. Chaque
export de la liste d'action (PDF/Excel) enregistre un instantané — qui,
quand, quantité recommandée par StockAid vs quantité finalement retenue.
"""
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import get_db, Base, engine
from app.core.security import get_password_hash
from app.models.officine import Officine
from app.models.user import User
from app.models.reference import Reference
from app.models.commande_validee import CommandeValidee


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
def ref_actionnable(db_session, officine):
    r = Reference(
        officine_id=officine.id,
        code="A001",
        designation="Doliprane 500mg",
        statut="CRITIQUE",
        classe="A",
        fsn="Fast",
        qte_a_commander=10,
        prix_cession=500,
        stock_actuel=5,
    )
    db_session.add(r)
    db_session.commit()
    db_session.refresh(r)
    return r


class TestEnregistrementAExport:
    def test_export_cree_un_enregistrement_avec_le_bon_utilisateur(self, client, token, db_session, user, ref_actionnable):
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/dashboard/export?format=xlsx", headers=headers)
        assert response.status_code == 200

        commandes = db_session.query(CommandeValidee).filter(
            CommandeValidee.officine_id == ref_actionnable.officine_id
        ).all()
        assert len(commandes) == 1
        assert commandes[0].user_id == user.id
        assert commandes[0].format == "xlsx"

        lignes = json.loads(commandes[0].lignes)
        assert len(lignes) == 1
        assert lignes[0]["code"] == "A001"
        assert lignes[0]["qte_recommandee"] == 10.0
        assert lignes[0]["qte_validee"] == 10.0

    def test_ecart_reflete_lajustement_manuel(self, client, token, db_session, ref_actionnable):
        headers = {"Authorization": f"Bearer {token}"}
        client.patch(
            f"/api/v1/references/{ref_actionnable.id}/ajustement-commande",
            json={"qte_a_commander_override": 25, "inclusion_manuelle": None},
            headers=headers,
        )
        client.get("/api/v1/dashboard/export?format=pdf", headers=headers)

        historique = client.get("/api/v1/dashboard/historique-commandes", headers=headers).json()
        assert len(historique) == 1
        assert historique[0]["nb_ecarts"] == 1
        ligne = historique[0]["lignes"][0]
        assert ligne["qte_recommandee"] == 10.0
        assert ligne["qte_validee"] == 25.0

    def test_chaque_export_cree_une_entree_distincte(self, client, token, db_session, ref_actionnable):
        headers = {"Authorization": f"Bearer {token}"}
        client.get("/api/v1/dashboard/export?format=xlsx", headers=headers)
        client.get("/api/v1/dashboard/export?format=pdf", headers=headers)

        historique = client.get("/api/v1/dashboard/historique-commandes", headers=headers).json()
        assert len(historique) == 2
        assert {h["format"] for h in historique} == {"xlsx", "pdf"}


class TestFiltrageHistorique:
    def test_filtre_par_utilisateur(self, client, token, db_session, officine, user, ref_actionnable):
        headers = {"Authorization": f"Bearer {token}"}
        client.get("/api/v1/dashboard/export?format=xlsx", headers=headers)

        # Un utilisateur différent, même officine (schéma déjà compatible
        # multi-utilisateur, section 7.3) : filtrer par user_id ne renvoie
        # que ses propres commandes.
        autre = User(
            email="autre@test.com",
            hashed_password=get_password_hash("password123"),
            officine_id=officine.id,
        )
        db_session.add(autre)
        db_session.commit()
        db_session.refresh(autre)

        response = client.get(f"/api/v1/dashboard/historique-commandes?user_id={autre.id}", headers=headers)
        assert response.status_code == 200
        assert response.json() == []

        response2 = client.get(f"/api/v1/dashboard/historique-commandes?user_id={user.id}", headers=headers)
        assert len(response2.json()) == 1
