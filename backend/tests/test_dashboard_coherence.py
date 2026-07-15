"""
Vérifie que le total "trésorerie immobilisée" de /dashboard/a-ne-pas-commander
reste cohérent avec /dashboard/kpis : les deux doivent arrondir une seule fois,
sur la somme finale — pas ligne par ligne avant d'additionner, sinon les deux
écrans affichent des totaux légèrement différents (bug constaté en usage réel).
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
def references_avec_stock_excedentaire(db_session, officine):
    """
    Plusieurs références avec un excédent de trésorerie non arrondi (ex: 0.333...),
    pour que l'arrondi ligne par ligne accumule un écart mesurable s'il persistait.
    """
    refs = []
    for i in range(30):
        r = Reference(
            officine_id=officine.id,
            code=f"REF{i:03d}",
            designation=f"Produit {i}",
            prix_cession=3.0,
            stock_actuel=100.0,
            niveau_recompletement=10.0,  # excédent = 90 unités
            tresorerie_liberee=90.0 * 3.0,  # 270.0, mais on force une valeur non ronde ci-dessous
            classe="C",
            fsn="Fast",
            statut="OK",
        )
        refs.append(r)
    # Force des valeurs non entières pour que l'arrondi ligne par ligne ait un effet mesurable
    for i, r in enumerate(refs):
        r.tresorerie_liberee = 270.0 + (i % 3) * 0.4  # 270.0 / 270.4 / 270.8
    db_session.add_all(refs)
    db_session.commit()
    return refs


class TestCoherenceTresorerie:
    def test_total_a_ne_pas_commander_coherent_avec_kpis(
        self, client, token, references_avec_stock_excedentaire
    ):
        headers = {"Authorization": f"Bearer {token}"}

        kpis = client.get("/api/v1/dashboard/kpis", headers=headers).json()
        lignes = client.get("/api/v1/dashboard/a-ne-pas-commander", headers=headers).json()

        total_somme_brute = sum(l["tresorerie_immobilisee"] for l in lignes)

        # Le total du Tableau de bord arrondit une seule fois sur la somme exacte —
        # sommer les valeurs brutes de "Quoi commander" doit donner le même résultat
        # une fois arrondi à son tour, à l'arrondi flottant près.
        assert round(total_somme_brute) == kpis["tresorerie_liberee_fcfa"]
