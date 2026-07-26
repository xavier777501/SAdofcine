"""
Vérifie GET /imports/etat : sert à proposer automatiquement le bon type
d'import (section 4bis — "le pharmacien ne doit jamais avoir à choisir").
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
from app.models.vente_mensuelle import VenteMensuelle
from app.models.import_log import ImportLog


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


class TestEtatImport:
    def test_pas_dhistorique_propose_type_historique(self, client, token):
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/imports/etat", headers=headers)
        assert response.status_code == 200
        assert response.json()["historique_initialise"] is False

    def test_avec_cmm_propose_type_commande(self, client, token, db_session, officine):
        db_session.add(Reference(
            officine_id=officine.id, code="A001", designation="Doliprane",
            stock_actuel=10, cmm=20.0,
        ))
        db_session.commit()

        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/imports/etat", headers=headers)
        assert response.status_code == 200
        assert response.json()["historique_initialise"] is True

    def test_nb_mois_historique_reflete_le_nombre_reel_de_mois_enregistres(self, client, token, db_session, officine):
        """
        L'écran d'import doit retrouver l'état réel (pas juste ce qui a été
        fait dans la session en cours) — donc ce chiffre doit venir de ce qui
        est vraiment stocké, ici 3 mois pour une référence.
        """
        ref = Reference(
            officine_id=officine.id, code="A001", designation="Doliprane",
            stock_actuel=10, cmm=5.0,
        )
        db_session.add(ref)
        db_session.commit()
        db_session.refresh(ref)

        for mois_index in (1, 2, 3):
            db_session.add(VenteMensuelle(reference_id=ref.id, mois_index=mois_index, quantite=10))
        db_session.commit()

        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/imports/etat", headers=headers)
        assert response.status_code == 200
        assert response.json()["nb_mois_historique"] == 3

    def test_nb_mois_historique_zero_sans_ventes(self, client, token):
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/imports/etat", headers=headers)
        assert response.status_code == 200
        assert response.json()["nb_mois_historique"] == 0


class TestStockInitialise:
    """
    Section 4bis : depuis que le Type 1 ne touche plus au stock, seul un
    import Type 2 ou Type 3 réussi donne un stock réel — l'écran doit pouvoir
    avertir tant que ce n'est pas encore arrivé.
    """

    def test_faux_sans_aucun_import(self, client, token):
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/imports/etat", headers=headers)
        assert response.json()["stock_initialise"] is False

    def test_faux_avec_seulement_un_import_historique_type1(self, client, token, db_session, officine):
        db_session.add(ImportLog(
            officine_id=officine.id, nom_fichier="historique.xlsx", statut="succes",
        ))
        db_session.commit()

        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/imports/etat", headers=headers)
        assert response.json()["stock_initialise"] is False

    def test_vrai_apres_un_import_commande_type2_reussi(self, client, token, db_session, officine):
        db_session.add(ImportLog(
            officine_id=officine.id, nom_fichier="commande.xlsx", statut="succes",
            sorties_totales=120.0,
        ))
        db_session.commit()

        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/imports/etat", headers=headers)
        assert response.json()["stock_initialise"] is True

    def test_vrai_apres_un_import_reception_type3_reussi(self, client, token, db_session, officine):
        db_session.add(ImportLog(
            officine_id=officine.id, nom_fichier="livraison.rtf", statut="succes",
            fournisseur="GROSSISTE FICTIF SARL",
        ))
        db_session.commit()

        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/imports/etat", headers=headers)
        assert response.json()["stock_initialise"] is True

    def test_faux_si_import_type2_en_erreur(self, client, token, db_session, officine):
        db_session.add(ImportLog(
            officine_id=officine.id, nom_fichier="commande.xlsx", statut="erreur",
            sorties_totales=120.0,
        ))
        db_session.commit()

        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/imports/etat", headers=headers)
        assert response.json()["stock_initialise"] is False
