"""
Vérifie POST /parametres/reinitialiser : remise à zéro complète et
irréversible des données métier d'une officine (bouton support / démo),
sans jamais supprimer le compte utilisateur ni l'officine elle-même, et
sans jamais affecter les données d'une autre officine.
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
from app.models.column_mapping import ColumnMapping
from app.models.delai_circuit import DelaiCircuit
from app.models.commande_validee import CommandeValidee
from app.models.parametre_officine import ParametreOfficine


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


def _peupler_donnees(db_session, officine, user):
    ref = Reference(
        officine_id=officine.id, code="A001", designation="Doliprane",
        stock_actuel=10, cmm=5.0,
    )
    db_session.add(ref)
    db_session.commit()
    db_session.refresh(ref)

    db_session.add(VenteMensuelle(reference_id=ref.id, mois_index=1, quantite=10))
    db_session.add(ImportLog(officine_id=officine.id, nom_fichier="test.xlsx", statut="succes"))
    db_session.add(ColumnMapping(officine_id=officine.id, champ_cible="code", colonne_source="Code Prod"))
    db_session.add(DelaiCircuit(officine_id=officine.id, circuit="Local", dl_moy_jours=5, dl_max_jours=10))
    db_session.add(CommandeValidee(
        officine_id=officine.id, user_id=user.id, format="pdf",
        lignes='[{"code": "A001"}]',
    ))
    db_session.add(ParametreOfficine(officine_id=officine.id, plafond_commande_fcfa=100000.0))
    db_session.commit()
    return ref


class TestReinitialisation:
    def test_mauvais_mot_de_passe_refuse_et_ne_touche_a_rien(self, client, token, db_session, officine, user):
        _peupler_donnees(db_session, officine, user)

        headers = {"Authorization": f"Bearer {token}"}
        response = client.post(
            "/api/v1/parametres/reinitialiser",
            json={"mot_de_passe": "mauvais_mot_de_passe"},
            headers=headers,
        )
        assert response.status_code == 401

        assert db_session.query(Reference).filter(Reference.officine_id == officine.id).count() == 1

    def test_bon_mot_de_passe_efface_toutes_les_donnees_mais_garde_le_compte(
        self, client, token, db_session, officine, user,
    ):
        _peupler_donnees(db_session, officine, user)

        headers = {"Authorization": f"Bearer {token}"}
        response = client.post(
            "/api/v1/parametres/reinitialiser",
            json={"mot_de_passe": "password123"},
            headers=headers,
        )
        assert response.status_code == 200

        assert db_session.query(Reference).filter(Reference.officine_id == officine.id).count() == 0
        assert db_session.query(VenteMensuelle).count() == 0
        assert db_session.query(ImportLog).filter(ImportLog.officine_id == officine.id).count() == 0
        assert db_session.query(ColumnMapping).filter(ColumnMapping.officine_id == officine.id).count() == 0
        assert db_session.query(DelaiCircuit).filter(DelaiCircuit.officine_id == officine.id).count() == 0
        assert db_session.query(CommandeValidee).filter(CommandeValidee.officine_id == officine.id).count() == 0
        assert db_session.query(ParametreOfficine).filter(ParametreOfficine.officine_id == officine.id).count() == 0

        # Le compte et l'officine restent intacts : la connexion doit toujours fonctionner.
        assert db_session.query(Officine).filter(Officine.id == officine.id).first() is not None
        assert db_session.query(User).filter(User.id == user.id).first() is not None
        relogin = client.post(
            "/api/v1/auth/login",
            json={"email": "pharma@test.com", "password": "password123"},
        )
        assert relogin.status_code == 200

    def test_naffecte_pas_les_donnees_dune_autre_officine(self, client, token, db_session, officine, user):
        _peupler_donnees(db_session, officine, user)

        autre_officine = Officine(nom="Autre Pharmacie")
        db_session.add(autre_officine)
        db_session.commit()
        db_session.refresh(autre_officine)
        autre_user = User(
            email="autre@test.com",
            hashed_password=get_password_hash("autre_password"),
            officine_id=autre_officine.id,
        )
        db_session.add(autre_user)
        db_session.commit()
        _peupler_donnees(db_session, autre_officine, autre_user)

        headers = {"Authorization": f"Bearer {token}"}
        response = client.post(
            "/api/v1/parametres/reinitialiser",
            json={"mot_de_passe": "password123"},
            headers=headers,
        )
        assert response.status_code == 200

        assert db_session.query(Reference).filter(Reference.officine_id == officine.id).count() == 0
        assert db_session.query(Reference).filter(Reference.officine_id == autre_officine.id).count() == 1


class TestReinitialisationHistorique:
    """
    Section 4bis : n'efface que ce que le Type 1 (historique) a produit —
    jamais le stock (Type 2/3), jamais les autres officines.
    """

    def _reference_complete(self, db_session, officine, **overrides):
        defaults = dict(
            officine_id=officine.id, code="A001", designation="Doliprane",
            stock_actuel=42, cmm=5.0, cmmax=8.0, sigma=1.2, ss=10.0, pc=20.0,
            classe="A", fsn="Fast", ved="Vital", statut="COMMANDER",
            qte_a_commander=15.0, couverture_jours=8.0, tresorerie_liberee=0.0,
        )
        defaults.update(overrides)
        ref = Reference(**defaults)
        db_session.add(ref)
        db_session.commit()
        db_session.refresh(ref)
        db_session.add(VenteMensuelle(reference_id=ref.id, mois_index=1, quantite=10))
        db_session.commit()
        return ref

    def test_mauvais_mot_de_passe_refuse(self, client, token, db_session, officine):
        self._reference_complete(db_session, officine)
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post(
            "/api/v1/parametres/reinitialiser-historique",
            json={"mot_de_passe": "faux"},
            headers=headers,
        )
        assert response.status_code == 401

    def test_efface_cmm_classe_fsn_ved_et_ventes_sans_toucher_au_stock(self, client, token, db_session, officine):
        ref = self._reference_complete(db_session, officine)

        headers = {"Authorization": f"Bearer {token}"}
        response = client.post(
            "/api/v1/parametres/reinitialiser-historique",
            json={"mot_de_passe": "password123"},
            headers=headers,
        )
        assert response.status_code == 200

        db_session.refresh(ref)
        assert ref.cmm is None
        assert ref.cmmax is None
        assert ref.sigma is None
        assert ref.ss is None
        assert ref.pc is None
        assert ref.classe is None
        assert ref.fsn is None
        assert ref.ved is None
        assert ref.statut is None
        assert ref.qte_a_commander is None
        # Jamais touché : c'est le rôle du Type 2/3, pas du Type 1.
        assert ref.stock_actuel == 42

        assert db_session.query(VenteMensuelle).filter(VenteMensuelle.reference_id == ref.id).count() == 0

    def test_naffecte_pas_une_autre_officine(self, client, token, db_session, officine):
        self._reference_complete(db_session, officine)

        autre_officine = Officine(nom="Autre Pharmacie")
        db_session.add(autre_officine)
        db_session.commit()
        db_session.refresh(autre_officine)
        autre_ref = self._reference_complete(db_session, autre_officine, code="B001")

        headers = {"Authorization": f"Bearer {token}"}
        response = client.post(
            "/api/v1/parametres/reinitialiser-historique",
            json={"mot_de_passe": "password123"},
            headers=headers,
        )
        assert response.status_code == 200

        db_session.refresh(autre_ref)
        assert autre_ref.cmm == 5.0


class TestReinitialisationStock:
    """
    Section 4bis/4ter : n'efface que ce que le Type 2/3 (commande/réception)
    a produit — jamais l'historique (Type 1), jamais les autres officines.
    """

    def test_mauvais_mot_de_passe_refuse(self, client, token, db_session, officine):
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post(
            "/api/v1/parametres/reinitialiser-stock",
            json={"mot_de_passe": "faux"},
            headers=headers,
        )
        assert response.status_code == 401

    def test_remet_le_stock_a_zero_sans_toucher_a_lhistorique(self, client, token, db_session, officine):
        ref = Reference(
            officine_id=officine.id, code="A001", designation="Doliprane",
            stock_actuel=42, sorties_derniere_commande=30.0, dans_dernier_import_commande=True,
            cmm=5.0, classe="A", fsn="Fast", ved="Vital", ss=10.0, pc=20.0,
        )
        db_session.add(ref)
        db_session.add(ParametreOfficine(officine_id=officine.id, mode_commande_ciblee=True))
        db_session.commit()
        db_session.refresh(ref)

        headers = {"Authorization": f"Bearer {token}"}
        response = client.post(
            "/api/v1/parametres/reinitialiser-stock",
            json={"mot_de_passe": "password123"},
            headers=headers,
        )
        assert response.status_code == 200

        db_session.refresh(ref)
        assert ref.stock_actuel == 0
        assert ref.sorties_derniere_commande is None
        assert ref.dans_dernier_import_commande is False
        # Jamais touchés : c'est le rôle du Type 1, pas du Type 2/3.
        assert ref.cmm == 5.0
        assert ref.classe == "A"
        assert ref.ved == "Vital"

        params = db_session.query(ParametreOfficine).filter(ParametreOfficine.officine_id == officine.id).first()
        assert params.mode_commande_ciblee is False

    def test_naffecte_pas_une_autre_officine(self, client, token, db_session, officine):
        autre_officine = Officine(nom="Autre Pharmacie")
        db_session.add(autre_officine)
        db_session.commit()
        db_session.refresh(autre_officine)
        autre_ref = Reference(officine_id=autre_officine.id, code="B001", designation="Efferalgan", stock_actuel=99)
        db_session.add(autre_ref)
        db_session.commit()
        db_session.refresh(autre_ref)

        headers = {"Authorization": f"Bearer {token}"}
        response = client.post(
            "/api/v1/parametres/reinitialiser-stock",
            json={"mot_de_passe": "password123"},
            headers=headers,
        )
        assert response.status_code == 200

        db_session.refresh(autre_ref)
        assert autre_ref.stock_actuel == 99


class TestReinitialisationJournal:
    """Vide seulement le tableau des imports — aucun effet sur le stock ni le calcul."""

    def test_mauvais_mot_de_passe_refuse(self, client, token, db_session, officine):
        db_session.add(ImportLog(officine_id=officine.id, nom_fichier="test.xlsx", statut="succes"))
        db_session.commit()
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post(
            "/api/v1/parametres/reinitialiser-journal",
            json={"mot_de_passe": "faux"},
            headers=headers,
        )
        assert response.status_code == 401
        assert db_session.query(ImportLog).filter(ImportLog.officine_id == officine.id).count() == 1

    def test_vide_le_journal_sans_toucher_au_stock_ni_a_lhistorique(self, client, token, db_session, officine):
        ref = Reference(
            officine_id=officine.id, code="A001", designation="Doliprane",
            stock_actuel=42, cmm=5.0,
        )
        db_session.add(ref)
        db_session.add(ImportLog(officine_id=officine.id, nom_fichier="commande.xlsx", statut="succes"))
        db_session.add(ImportLog(officine_id=officine.id, nom_fichier="historique.xlsx", statut="succes"))
        db_session.commit()
        db_session.refresh(ref)

        headers = {"Authorization": f"Bearer {token}"}
        response = client.post(
            "/api/v1/parametres/reinitialiser-journal",
            json={"mot_de_passe": "password123"},
            headers=headers,
        )
        assert response.status_code == 200
        assert db_session.query(ImportLog).filter(ImportLog.officine_id == officine.id).count() == 0

        db_session.refresh(ref)
        assert ref.stock_actuel == 42
        assert ref.cmm == 5.0

    def test_naffecte_pas_le_journal_dune_autre_officine(self, client, token, db_session, officine):
        db_session.add(ImportLog(officine_id=officine.id, nom_fichier="test.xlsx", statut="succes"))

        autre_officine = Officine(nom="Autre Pharmacie")
        db_session.add(autre_officine)
        db_session.commit()
        db_session.refresh(autre_officine)
        db_session.add(ImportLog(officine_id=autre_officine.id, nom_fichier="autre.xlsx", statut="succes"))
        db_session.commit()

        headers = {"Authorization": f"Bearer {token}"}
        response = client.post(
            "/api/v1/parametres/reinitialiser-journal",
            json={"mot_de_passe": "password123"},
            headers=headers,
        )
        assert response.status_code == 200
        assert db_session.query(ImportLog).filter(ImportLog.officine_id == officine.id).count() == 0
        assert db_session.query(ImportLog).filter(ImportLog.officine_id == autre_officine.id).count() == 1
