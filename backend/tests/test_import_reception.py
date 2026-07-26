"""
Section 4quater du cahier des charges V9 : import réception fournisseur
(Type 3), bon de livraison au format RTF généré par Logpharma. Remplace
directement stock_actuel par "Stock Fin." — jamais d'addition, jamais de
recalcul de CMM/sigma/classe ABC/FSN/VED (données de fond du moteur,
issues uniquement de l'import historique Type 1).
"""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import get_db, Base, engine
from app.core.security import get_password_hash
from app.models.officine import Officine
from app.models.user import User
from app.models.reference import Reference
from app.services.file_parser import parse_reception_logpharma

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "reception_test_fictive.rtf")


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


def _rtf_bytes():
    with open(FIXTURE, "rb") as f:
        return f.read()


class TestParseReceptionLogpharma:
    """Vérifie le parseur RTF directement, contre le vrai fichier fourni par le client."""

    def test_extrait_les_15_lignes(self):
        resultat = parse_reception_logpharma(_rtf_bytes())
        assert len(resultat["lignes"]) == 15

    def test_extrait_fournisseur_et_bl(self):
        resultat = parse_reception_logpharma(_rtf_bytes())
        assert resultat["fournisseur"] == "GROSSISTE FICTIF SARL"
        assert resultat["bl_numero"] == "000001"
        assert resultat["bl_date"] == "01/07/2026"

    def test_premiere_ligne_correcte(self):
        resultat = parse_reception_logpharma(_rtf_bytes())
        ligne = resultat["lignes"][0]
        assert ligne["code"] == "TST0001"
        assert ligne["designation"] == "PARACETAMOL 500MG CPR B/16"
        assert ligne["qte_livree"] == 5.0
        assert ligne["stock_init"] == 3.0
        assert ligne["stock_fin"] == 8.0
        assert ligne["prix_cession"] == 2450.0
        assert ligne["prix_public"] == 3185.0

    def test_stock_fin_egale_stock_init_plus_qte_livree_partout(self):
        resultat = parse_reception_logpharma(_rtf_bytes())
        for ligne in resultat["lignes"]:
            assert ligne["stock_fin"] == ligne["stock_init"] + ligne["qte_livree"]

    def test_fichier_non_rtf_leve_une_erreur_claire(self):
        with pytest.raises(ValueError):
            parse_reception_logpharma(b"ceci n'est pas un fichier RTF valide")


class TestImportReceptionEndpoint:
    def _creer_reference(self, db_session, officine, code="TST0001", stock=3, prix_cession=2450, prix_public=3185):
        ref = Reference(
            officine_id=officine.id,
            code=code,
            designation="PARACETAMOL 500MG CPR B/16",
            stock_actuel=stock,
            prix_cession=prix_cession,
            prix_public=prix_public,
            statut="RUPTURE",
            classe="A",
            fsn="Fast",
            cmm=100.0,
            sigma=10.0,
            ss=16.45,
            pc=116.45,
            niveau_recompletement=20.0,  # S bas : stock_fin (8) doit repasser au-dessus
            qte_a_commander=17.0,
        )
        db_session.add(ref)
        db_session.commit()
        db_session.refresh(ref)
        return ref

    def _importer(self, client, headers):
        return client.post(
            "/api/v1/imports/reception",
            files={"file": ("bl.doc", _rtf_bytes(), "application/rtf")},
            headers=headers,
        )

    def test_stock_actuel_remplace_par_stock_fin(self, client, token, db_session, officine):
        headers = {"Authorization": f"Bearer {token}"}
        ref = self._creer_reference(db_session, officine)

        response = self._importer(client, headers)
        assert response.status_code == 200
        body = response.json()
        assert body["nb_lignes_ok"] == 1
        assert body["nb_lignes_erreur"] == 14  # les 14 autres codes du fichier sont inconnus ici
        assert body["fournisseur"] == "GROSSISTE FICTIF SARL"

        db_session.refresh(ref)
        assert ref.stock_actuel == 8.0  # remplacement direct par Stock Fin., pas une addition

    def test_cmm_sigma_classe_fsn_ved_jamais_touches(self, client, token, db_session, officine):
        headers = {"Authorization": f"Bearer {token}"}
        ref = self._creer_reference(db_session, officine)
        ref.ved = "Vital"
        db_session.commit()

        self._importer(client, headers)

        db_session.refresh(ref)
        assert ref.cmm == 100.0
        assert ref.sigma == 10.0
        assert ref.classe == "A"
        assert ref.fsn == "Fast"
        assert ref.ved == "Vital"
        assert ref.ss == 16.45
        assert ref.pc == 116.45

    def test_reference_livree_sort_de_la_liste_daction_si_stock_suffisant(self, client, token, db_session, officine):
        headers = {"Authorization": f"Bearer {token}"}
        # RUPTURE initialement (stock=0) : le statut dépend de SS/PC, pas
        # seulement de S — on les abaisse pour que Stock Fin. (8) redevienne OK.
        ref = self._creer_reference(db_session, officine, stock=0)
        ref.ss = 2.0
        ref.pc = 5.0
        ref.niveau_recompletement = 5.0
        db_session.commit()

        self._importer(client, headers)

        response = client.get("/api/v1/dashboard/liste-action", headers=headers)
        codes = [l["code"] for l in response.json()]
        assert "TST0001" not in codes

    def test_code_inconnu_signale_en_erreur_sans_planter(self, client, token, officine):
        headers = {"Authorization": f"Bearer {token}"}
        response = self._importer(client, headers)
        assert response.status_code == 200
        body = response.json()
        assert body["nb_lignes_total"] == 15
        assert body["nb_lignes_ok"] == 0
        assert body["nb_lignes_erreur"] == 15

    def test_fournisseur_visible_dans_historique_des_imports(self, client, token, db_session, officine):
        headers = {"Authorization": f"Bearer {token}"}
        self._creer_reference(db_session, officine)
        self._importer(client, headers)

        historique = client.get("/api/v1/imports/", headers=headers).json()
        assert historique[0]["fournisseur"] == "GROSSISTE FICTIF SARL"
