"""
Section 7.2 du cahier des charges V9 : notification quotidienne. Envoi
opportuniste — StockAid ne tournant que lorsqu'on l'ouvre, l'envoi se
déclenche au premier chargement du tableau de bord dans la journée, une
fois l'heure configurée passée, jamais plus d'une fois par jour.
"""
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import get_db, Base, engine
from app.core.security import get_password_hash
from app.models.officine import Officine
from app.models.user import User
from app.models.reference import Reference
from app.models.parametre_officine import ParametreOfficine
from app.services.notification_quotidienne import verifier_et_envoyer_notification_quotidienne


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
def params_actifs(db_session, officine):
    p = ParametreOfficine(
        officine_id=officine.id,
        notification_active=True,
        notification_heure="08:00",
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


@pytest.fixture
def ref_qualifiee(db_session, officine):
    r = Reference(
        officine_id=officine.id,
        code="A001",
        designation="Doliprane 500mg",
        statut="CRITIQUE",
        classe="A",
        fsn="Fast",
        cmm=100.0,
        pc=50.0,
        stock_actuel=10,
        prix_public=800,
    )
    db_session.add(r)
    db_session.commit()
    return r


class TestEnvoiOpportuniste:
    def test_pas_denvoi_si_desactive(self, db_session, officine, ref_qualifiee):
        params = ParametreOfficine(officine_id=officine.id, notification_active=False)
        db_session.add(params)
        db_session.commit()

        maintenant = datetime(2026, 7, 24, 9, 0)
        verifier_et_envoyer_notification_quotidienne(officine, params, db_session, maintenant)
        assert params.notification_derniere_envoyee_le is None

    def test_pas_denvoi_avant_lheure_configuree(self, db_session, officine, params_actifs, ref_qualifiee, user):
        maintenant = datetime(2026, 7, 24, 6, 30)  # avant 08:00
        verifier_et_envoyer_notification_quotidienne(officine, params_actifs, db_session, maintenant)
        assert params_actifs.notification_derniere_envoyee_le is None

    def test_envoi_declenche_apres_lheure_et_marque_la_date(self, db_session, officine, params_actifs, ref_qualifiee, user):
        maintenant = datetime(2026, 7, 24, 9, 0)
        verifier_et_envoyer_notification_quotidienne(officine, params_actifs, db_session, maintenant)
        assert params_actifs.notification_derniere_envoyee_le == date(2026, 7, 24)

    def test_pas_de_double_envoi_le_meme_jour(self, db_session, officine, params_actifs, ref_qualifiee, user):
        maintenant = datetime(2026, 7, 24, 9, 0)
        verifier_et_envoyer_notification_quotidienne(officine, params_actifs, db_session, maintenant)
        # Un second appel plus tard le même jour ne doit rien re-déclencher
        # (on ne peut pas observer directement l'absence d'envoi ici, mais la
        # date reste inchangée et la fonction ressort immédiatement).
        maintenant2 = datetime(2026, 7, 24, 15, 0)
        verifier_et_envoyer_notification_quotidienne(officine, params_actifs, db_session, maintenant2)
        assert params_actifs.notification_derniere_envoyee_le == date(2026, 7, 24)

    def test_marque_la_date_meme_sans_reference_qualifiee(self, db_session, officine, params_actifs, user):
        # Aucune référence en RUPTURE/CRITIQUE classe A/B : le cahier des
        # charges dit "le message peut être omis", mais on ne veut pas
        # recalculer à chaque rechargement du tableau de bord.
        maintenant = datetime(2026, 7, 24, 9, 0)
        verifier_et_envoyer_notification_quotidienne(officine, params_actifs, db_session, maintenant)
        assert params_actifs.notification_derniere_envoyee_le == date(2026, 7, 24)

    def test_nouveau_jour_redeclenche_lenvoi(self, db_session, officine, params_actifs, ref_qualifiee, user):
        params_actifs.notification_derniere_envoyee_le = date(2026, 7, 23)
        db_session.commit()
        maintenant = datetime(2026, 7, 24, 9, 0)
        verifier_et_envoyer_notification_quotidienne(officine, params_actifs, db_session, maintenant)
        assert params_actifs.notification_derniere_envoyee_le == date(2026, 7, 24)


class TestIntegrationDashboard:
    def test_kpis_declenche_la_verification_sans_planter(self, client, db_session, officine, user):
        headers_login = client.post(
            "/api/v1/auth/login",
            json={"email": "pharma@test.com", "password": "password123"},
        )
        token = headers_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Active la notification via les Réglages, comme le ferait le pharmacien
        response = client.patch(
            "/api/v1/parametres",
            json={"notification_active": True, "notification_heure": "00:00"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["notification_active"] is True

        # /kpis ne doit jamais planter, notification comprise
        response_kpis = client.get("/api/v1/dashboard/kpis", headers=headers)
        assert response_kpis.status_code == 200

        params = db_session.query(ParametreOfficine).filter(
            ParametreOfficine.officine_id == officine.id
        ).first()
        assert params.notification_derniere_envoyee_le == date.today()
