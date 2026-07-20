"""
Vérifie l'encart d'alerte "Références stratégiques manquées" (section 7.0) :
périmètre (classe A/B, RUPTURE/CRITIQUE, Non-moving totalement exclu même
Vital), formule des jours de rupture/ventes perdues, et le bouton
"Commander ces références".
"""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import get_db, Base, engine
from app.core.security import get_password_hash
from app.models.officine import Officine
from app.models.user import User
from app.models.reference import Reference
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


@pytest.fixture
def dernier_import(db_session, officine):
    """Dernier import il y a exactement 5 jours (RUPTURE = jours depuis cet import)."""
    log = ImportLog(
        officine_id=officine.id,
        nom_fichier="logpharma.xlsx",
        statut="succes",
        nb_lignes_total=1,
        nb_lignes_ok=1,
        nb_lignes_erreur=0,
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)
    log.created_at = datetime.utcnow() - timedelta(days=5)
    db_session.commit()
    return log


def _ref(officine_id, code, classe="A", statut="RUPTURE", fsn="Fast", ved=None,
         cmm=250.0, pc=100.0, stock_actuel=0.0, prix_public=84.0):
    return Reference(
        officine_id=officine_id,
        code=code,
        designation=f"Produit {code}",
        classe=classe,
        statut=statut,
        fsn=fsn,
        ved=ved,
        cmm=cmm,
        pc=pc,
        stock_actuel=stock_actuel,
        prix_public=prix_public,
    )


class TestAlertesStrategiques:
    def test_rupture_utilise_les_jours_depuis_le_dernier_import(self, client, token, db_session, officine, dernier_import):
        db_session.add(_ref(officine.id, "A001", statut="RUPTURE", cmm=250.0, prix_public=84.0))
        db_session.commit()

        headers = {"Authorization": f"Bearer {token}"}
        body = client.get("/api/v1/dashboard/alertes-strategiques", headers=headers).json()

        assert body["nb_references"] == 1
        ligne = body["references"][0]
        assert ligne["jours_rupture"] == 5
        # Exemple du cahier des charges : (250/30) x 5 x 84 = 3500 (arrondi)
        assert ligne["ventes_perdues_fcfa"] == round(250 / 30 * 5 * 84, 0)

    def test_critique_utilise_pc_moins_stock_sur_cmm_jour_arrondi_superieur(self, client, token, db_session, officine, dernier_import):
        # cmm/jour = 300/30 = 10 ; (pc - stock)/cmm_jour = (100-40)/10 = 6 -> pas d'arrondi nécessaire ici
        db_session.add(_ref(officine.id, "B002", statut="CRITIQUE", cmm=300.0, pc=100.0, stock_actuel=40.0, prix_public=50.0))
        db_session.commit()

        headers = {"Authorization": f"Bearer {token}"}
        body = client.get("/api/v1/dashboard/alertes-strategiques", headers=headers).json()

        ligne = body["references"][0]
        assert ligne["jours_rupture"] == 6
        assert ligne["ventes_perdues_fcfa"] == round(300 / 30 * 6 * 50, 0)

    def test_arrondi_a_lentier_superieur_pour_critique(self, client, token, db_session, officine, dernier_import):
        # cmm/jour = 10 ; (100-45)/10 = 5.5 -> arrondi à 6 (entier supérieur)
        db_session.add(_ref(officine.id, "C003", statut="CRITIQUE", cmm=300.0, pc=100.0, stock_actuel=45.0))
        db_session.commit()

        headers = {"Authorization": f"Bearer {token}"}
        body = client.get("/api/v1/dashboard/alertes-strategiques", headers=headers).json()
        assert body["references"][0]["jours_rupture"] == 6

    def test_classe_c_exclue(self, client, token, db_session, officine, dernier_import):
        db_session.add(_ref(officine.id, "D004", classe="C", statut="RUPTURE"))
        db_session.commit()
        headers = {"Authorization": f"Bearer {token}"}
        body = client.get("/api/v1/dashboard/alertes-strategiques", headers=headers).json()
        assert body["nb_references"] == 0

    def test_non_moving_exclu_meme_si_vital(self, client, token, db_session, officine, dernier_import):
        db_session.add(_ref(officine.id, "E005", statut="RUPTURE", fsn="Non-moving", ved="Vital"))
        db_session.commit()
        headers = {"Authorization": f"Bearer {token}"}
        body = client.get("/api/v1/dashboard/alertes-strategiques", headers=headers).json()
        assert body["nb_references"] == 0

    def test_statut_ok_ou_commander_exclu(self, client, token, db_session, officine, dernier_import):
        db_session.add(_ref(officine.id, "F006", statut="OK"))
        db_session.add(_ref(officine.id, "G007", statut="COMMANDER"))
        db_session.commit()
        headers = {"Authorization": f"Bearer {token}"}
        body = client.get("/api/v1/dashboard/alertes-strategiques", headers=headers).json()
        assert body["nb_references"] == 0

    def test_trie_par_ventes_perdues_decroissantes_et_total_correct(self, client, token, db_session, officine, dernier_import):
        petit = _ref(officine.id, "PETIT", statut="RUPTURE", cmm=10.0, prix_public=10.0)
        gros = _ref(officine.id, "GROS", statut="RUPTURE", cmm=1000.0, prix_public=500.0)
        db_session.add_all([petit, gros])
        db_session.commit()

        headers = {"Authorization": f"Bearer {token}"}
        body = client.get("/api/v1/dashboard/alertes-strategiques", headers=headers).json()

        assert [l["code"] for l in body["references"]] == ["GROS", "PETIT"]
        attendu_total = round(sum(l["ventes_perdues_fcfa"] for l in body["references"]), 0)
        assert body["ventes_perdues_totales_fcfa"] == attendu_total

    def test_aucun_import_jamais_fait_jours_rupture_zero(self, client, token, db_session, officine):
        # Pas de fixture dernier_import : aucun ImportLog en base.
        db_session.add(_ref(officine.id, "H008", statut="RUPTURE"))
        db_session.commit()
        headers = {"Authorization": f"Bearer {token}"}
        body = client.get("/api/v1/dashboard/alertes-strategiques", headers=headers).json()
        assert body["references"][0]["jours_rupture"] == 0
        assert body["references"][0]["ventes_perdues_fcfa"] == 0.0

    def test_inclure_tout_force_inclusion_manuelle_sur_les_qualifiees_seulement(self, client, token, db_session, officine, dernier_import):
        qualifiee = _ref(officine.id, "Q001", statut="RUPTURE")
        non_qualifiee_classe_c = _ref(officine.id, "Q002", classe="C", statut="RUPTURE")
        non_qualifiee_non_moving = _ref(officine.id, "Q003", statut="RUPTURE", fsn="Non-moving")
        db_session.add_all([qualifiee, non_qualifiee_classe_c, non_qualifiee_non_moving])
        db_session.commit()

        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("/api/v1/dashboard/alertes-strategiques/inclure-tout", headers=headers)
        assert response.status_code == 200
        assert response.json()["nb_references_incluses"] == 1

        db_session.refresh(qualifiee)
        db_session.refresh(non_qualifiee_classe_c)
        db_session.refresh(non_qualifiee_non_moving)
        assert qualifiee.inclusion_manuelle == "inclure"
        assert non_qualifiee_classe_c.inclusion_manuelle is None
        assert non_qualifiee_non_moving.inclusion_manuelle is None
