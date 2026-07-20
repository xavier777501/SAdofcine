"""
Vérifie la logique du plafond budgétaire de commande (section 6.7, V7) :
priorisation en 8 niveaux centrée classe ABC + rotation Fast/Slow (le VED ne
compte plus qu'aux deux tout premiers niveaux), exception absolue
RUPTURE+Vital hors plafond, arrêt séquentiel dès que le montant cumulé
atteint le seuil.
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
from app.services.plafond_commande import prioriser_et_plafonner, _priorite


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
         qte_override=None, inclusion=None):
    return Reference(
        officine_id=officine_id,
        code=code,
        designation=f"Produit {code}",
        statut=statut,
        ved=ved,
        classe=classe,
        fsn=fsn,
        qte_a_commander=qte,
        qte_a_commander_override=qte_override,
        inclusion_manuelle=inclusion,
        prix_cession=prix,
        stock_actuel=5,
    )


class TestPriorite:
    def test_ordre_des_8_niveaux(self, officine):
        oid = officine.id
        cas = [
            (_ref(oid, "A", "RUPTURE", ved="Vital"), 0),
            (_ref(oid, "B", "CRITIQUE", ved="Vital", classe="C", fsn="Slow"), 1),
            (_ref(oid, "C", "RUPTURE", classe="A", fsn="Fast"), 2),
            (_ref(oid, "D", "RUPTURE", classe="A", fsn="Slow"), 3),
            (_ref(oid, "E", "RUPTURE", classe="B", fsn="Fast"), 4),
            (_ref(oid, "F", "CRITIQUE", classe="A", fsn="Fast"), 5),
            (_ref(oid, "G", "CRITIQUE", classe="A", fsn="Slow"), 6),
            (_ref(oid, "H", "CRITIQUE", classe="B", fsn="Fast"), 7),
            (_ref(oid, "I", "COMMANDER", classe="A", fsn="Fast"), 8),
            (_ref(oid, "J", "RUPTURE", classe="B", fsn="Slow"), 8),
            (_ref(oid, "K", "CRITIQUE", classe="C"), 8),
        ]
        for ref, attendu in cas:
            assert _priorite(ref) == attendu, f"{ref.code} attendu {attendu}"


class TestPrioriserEtPlafonner:
    def test_rupture_vital_toujours_hors_plafond(self, officine):
        refs = [
            _ref(officine.id, "VIT1", "RUPTURE", ved="Vital", qte=100, prix=100000),
        ]
        resultat = prioriser_et_plafonner(refs, plafond=1.0)  # plafond ridiculement bas
        assert len(resultat["hors_plafond"]) == 1
        assert resultat["hors_plafond"][0]["code"] == "VIT1"
        assert len(resultat["inclus"]) == 0
        assert len(resultat["reporte"]) == 0

    def test_sans_plafond_tout_est_inclus(self, officine):
        refs = [
            _ref(officine.id, "A", "RUPTURE", ved="Essentiel", classe="A", qte=10, prix=1000),
            _ref(officine.id, "B", "COMMANDER", classe="C", qte=10, prix=1000),
        ]
        resultat = prioriser_et_plafonner(refs, plafond=None)
        assert resultat["sans_restriction"] is True
        assert len(resultat["inclus"]) == 2
        assert len(resultat["reporte"]) == 0

        resultat_zero = prioriser_et_plafonner(refs, plafond=0)
        assert resultat_zero["sans_restriction"] is True

    def test_arret_sequentiel_au_plafond(self, officine):
        # 3 références, chacune 1000 FCFA, priorités décroissantes (2, 4, 8)
        refs = [
            _ref(officine.id, "P2", "RUPTURE", classe="A", fsn="Fast", qte=1, prix=1000),
            _ref(officine.id, "P4", "RUPTURE", classe="B", fsn="Fast", qte=1, prix=1000),
            _ref(officine.id, "P8", "COMMANDER", classe="C", qte=1, prix=1000),
        ]
        resultat = prioriser_et_plafonner(refs, plafond=1500)
        # Seule la première (1000 FCFA) rentre ; la 2e ferait dépasser 1500 -> reportée,
        # et la 3e est reportée aussi même si elle rentrerait seule (arrêt séquentiel).
        assert [l["code"] for l in resultat["inclus"]] == ["P2"]
        assert [l["code"] for l in resultat["reporte"]] == ["P4", "P8"]
        assert resultat["budget_utilise"] == 1000
        assert resultat["montant_reporte"] == 2000

    def test_alerte_rupture_non_vitale_reportee(self, officine):
        refs = [
            _ref(officine.id, "GROS", "RUPTURE", ved="Essentiel", classe="A", qte=100, prix=100000),
            _ref(officine.id, "PETIT_RUPTURE", "RUPTURE", ved="Désirable", qte=1, prix=1000),
        ]
        resultat = prioriser_et_plafonner(refs, plafond=100)
        assert resultat["rupture_non_vitale_reportee"] is True

    def test_statut_ok_exclu(self, officine):
        refs = [_ref(officine.id, "OK1", "OK", classe="A", qte=0, prix=1000)]
        resultat = prioriser_et_plafonner(refs, plafond=None)
        assert resultat["hors_plafond"] == []
        assert resultat["inclus"] == []
        assert resultat["reporte"] == []


class TestArbitrageManuel:
    """Section 6.7 : le pharmacien garde toujours la main sur la commande."""

    def test_exclusion_manuelle_retire_de_toutes_les_listes(self, officine):
        refs = [
            _ref(officine.id, "VIT1", "RUPTURE", ved="Vital", qte=10, prix=1000, inclusion="exclure"),
            _ref(officine.id, "CMD1", "COMMANDER", classe="B", qte=10, prix=1000, inclusion="exclure"),
        ]
        resultat = prioriser_et_plafonner(refs, plafond=None)
        assert resultat["hors_plafond"] == []
        assert resultat["inclus"] == []
        assert resultat["reporte"] == []

    def test_inclusion_manuelle_force_une_reference_ok_hors_plafond(self, officine):
        # Une inclusion manuelle est une garantie explicite : elle doit
        # vraiment passer hors plafond, pas seulement entrer dans le tri
        # normal (où le plafond pourrait quand même la reporter).
        refs = [_ref(officine.id, "OK1", "OK", classe="A", qte=0, prix=1000, inclusion="inclure")]
        resultat = prioriser_et_plafonner(refs, plafond=None)
        assert [l["code"] for l in resultat["hors_plafond"]] == ["OK1"]
        assert resultat["inclus"] == []

    def test_inclusion_manuelle_bypasse_reellement_le_plafond(self, officine):
        # Bug corrigé : avant, forcer l'inclusion d'une référence déjà
        # actionnable (RUPTURE/CRITIQUE/COMMANDER) ne changeait rien puisque
        # rien ne l'exemptait du plafond — elle pouvait quand même finir
        # reportée, rendant le bouton "Inclure quand même (hors plafond)"
        # inopérant. Ici, plafond=100 est trop bas pour inclure P1 (1000 FCFA)
        # via le tri normal, mais l'inclusion manuelle doit la faire passer.
        refs = [_ref(officine.id, "P1", "CRITIQUE", classe="C", qte=1, prix=1000, inclusion="inclure")]
        resultat = prioriser_et_plafonner(refs, plafond=100)
        assert [l["code"] for l in resultat["hors_plafond"]] == ["P1"]
        assert resultat["reporte"] == []
        assert resultat["inclus"] == []

    def test_override_quantite_remplace_la_suggestion(self, officine):
        refs = [_ref(officine.id, "A", "COMMANDER", classe="B", qte=10, prix=1000, qte_override=25)]
        resultat = prioriser_et_plafonner(refs, plafond=None)
        ligne = resultat["inclus"][0]
        assert ligne["qte_a_commander"] == 25
        assert ligne["qte_a_commander_auto"] == 10
        assert ligne["valeur_fcfa"] == 25000

    def test_override_quantite_impacte_le_calcul_du_plafond(self, officine):
        # Suggestion moteur = 1 (1000 FCFA), mais le pharmacien force 5 (5000 FCFA) :
        # le plafond doit se baser sur le montant réellement retenu.
        refs = [_ref(officine.id, "A", "COMMANDER", classe="B", qte=1, prix=1000, qte_override=5)]
        resultat = prioriser_et_plafonner(refs, plafond=4000)
        assert resultat["inclus"] == []
        assert [l["code"] for l in resultat["reporte"]] == ["A"]


class TestEndpointCommandePlafonnee:
    def test_endpoint_retourne_structure_coherente(self, client, token, db_session, officine):
        db_session.add(_ref(officine.id, "V1", "RUPTURE", ved="Vital", qte=10, prix=5000))
        db_session.commit()

        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/dashboard/commande-plafonnee", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["sans_restriction"] is True
        assert len(body["hors_plafond"]) == 1
        assert body["hors_plafond"][0]["code"] == "V1"
