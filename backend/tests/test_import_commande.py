"""
Vérifie l'import Type 2 (POST /imports/commande, format Logpharma fixe) :
il ne doit jamais toucher CMM/sigma/ABC/FSN/prix — seulement stock_actuel —
et déclenche uniquement le recalcul léger des quantités à commander.
"""
import io

import pandas as pd
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
def reference_deja_calculee(db_session, officine):
    """
    Simule une référence déjà passée par un import historique : CMM/sigma/SS/PC/S
    déjà calculés, comme si le moteur SAD avait tourné le mois dernier.
    """
    ref = Reference(
        officine_id=officine.id,
        code="A001",
        designation="Doliprane 500mg",
        prix_cession=500.0,
        prix_public=800.0,
        stock_actuel=5.0,
        classe="A",
        fsn="Fast",
        cmm=100.0,
        cmmax=130.0,
        sigma=10.0,
        z_service=1.645,
        ss=16.45,
        pc=116.45,
        niveau_recompletement=250.0,
        statut="RUPTURE",
    )
    db_session.add(ref)
    db_session.commit()
    db_session.refresh(ref)

    db_session.add(VenteMensuelle(reference_id=ref.id, mois_index=1, quantite=100))
    db_session.commit()

    return ref


def _fichier_logpharma(code="A001", designation="Doliprane 500mg", stock=180, sorties=90,
                       prix_cession=550, prix_public=900):
    """
    Reproduit le format fixe 'Listing de Produit à Commander' décrit au CDC V3
    section 4bis : ligne 1 = nom pharmacie, ligne 2 = titre/date, ligne 3 = en-têtes,
    puis les données, puis 3 lignes de totaux/pagination à ignorer.
    """
    lignes_brutes = [
        ["Pharmacie Fictive", None, None, None, None, None, None, None, None, None, None, None],
        ["Listing de Produit à Commander - 09/07/2026", None, None, None, None, None, None, None, None, None, None, None],
        ["Code Prod", "A Commander", "Désignation", "Qté Sal.", "E", "Sorties", "G", "H",
         "Prix Ces.", "Prix Public", "K", "FOURNISSEUR"],
        [code, 999, designation, stock, None, sorties, None, None, prix_cession, prix_public, None, "Local"],
        ["TOTAL", None, None, None, None, None, None, None, None, None, None, None],
        ["", None, None, None, None, None, None, None, None, None, None, None],
        ["Page 1/1", None, None, None, None, None, None, None, None, None, None, None],
    ]
    buf = io.BytesIO()
    pd.DataFrame(lignes_brutes).to_excel(buf, index=False, header=False)
    buf.seek(0)
    return buf


class TestImportCommandeLogpharma:
    def test_stock_mis_a_jour_cmm_abc_fsn_prix_inchanges(self, client, token, db_session, reference_deja_calculee):
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/v1/imports/commande",
            files={"file": ("logpharma.xlsx", _fichier_logpharma(stock=180, sorties=90), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["nb_lignes_ok"] == 1
        assert body["nb_lignes_erreur"] == 0

        db_session.refresh(reference_deja_calculee)
        ref = reference_deja_calculee

        # Stock rafraîchi depuis le fichier Logpharma
        assert ref.stock_actuel == 180.0

        # CMM/sigma/ABC/FSN/SS/PC/S/prix inchangés — le CDC dit "il ne met à
        # jour que le stock actuel" (section 4bis) ; seul l'import historique
        # peut modifier ces données de fond du moteur.
        assert ref.cmm == 100.0
        assert ref.sigma == 10.0
        assert ref.classe == "A"
        assert ref.fsn == "Fast"
        assert ref.ss == 16.45
        assert ref.pc == 116.45
        assert ref.niveau_recompletement == 250.0
        assert ref.prix_cession == 500.0
        assert ref.prix_public == 800.0

        # Statut et quantité à commander recalculés à partir du nouveau stock
        assert ref.statut == "OK"  # stock (180) > pc (116.45)
        assert ref.qte_a_commander == 70.0  # S(250) - stock(180)

        # Les ventes mensuelles de l'historique ne sont jamais touchées
        ventes = db_session.query(VenteMensuelle).filter(VenteMensuelle.reference_id == ref.id).all()
        assert len(ventes) == 1
        assert ventes[0].quantite == 100

    def test_code_inconnu_signale_en_erreur_sans_planter(self, client, token, reference_deja_calculee):
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post(
            "/api/v1/imports/commande",
            files={"file": ("logpharma.xlsx", _fichier_logpharma(code="INCONNU"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["nb_lignes_ok"] == 0
        assert body["nb_lignes_erreur"] == 1
