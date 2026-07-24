"""
Vérifie l'import Type 1 "annuel combiné" (POST /imports/historique-logpharma-annuel) :
un seul fichier Logpharma (même format fixe) couvrant une longue période en un
seul total de sorties. Ne doit calculer QUE le CMM — jamais CMMax/sigma/SS/PC/
statut, qui exigent un détail mensuel que ce fichier ne contient pas.
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


def _fichier_logpharma(code="A001", designation="Doliprane 500mg", stock=50, sorties=1200,
                       prix_cession=550, prix_public=900, reserve=None):
    """Même format fixe 'Listing de Produit à Commander' que les autres imports Logpharma."""
    lignes_brutes = [
        ["Pharmacie Fictive", None, None, None, None, None, None, None, None, None, None, None],
        ["Listing de Produit à Commander - 09/07/2026", None, None, None, None, None, None, None, None, None, None, None],
        ["Code Prod", "A Commander", "Désignation", "Qté Sal.", "Réserve", "Sorties", "G", "H",
         "Prix Ces.", "Prix Public", "K", "FOURNISSEUR"],
        [code, 999, designation, stock, reserve, sorties, None, None, prix_cession, prix_public, None, "Local"],
        ["TOTAL", None, None, None, None, None, None, None, None, None, None, None],
        ["", None, None, None, None, None, None, None, None, None, None, None],
        ["Page 1/1", None, None, None, None, None, None, None, None, None, None, None],
    ]
    buf = io.BytesIO()
    pd.DataFrame(lignes_brutes).to_excel(buf, index=False, header=False)
    buf.seek(0)
    return buf


class TestImportHistoriqueAnnuel:
    def test_cmm_correct_reste_des_champs_non_calcules(self, client, token, db_session):
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post(
            "/api/v1/imports/historique-logpharma-annuel",
            files={"file": ("annuel.xlsx", _fichier_logpharma(stock=50, sorties=1200), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["nb_lignes_ok"] == 1
        assert body["nb_lignes_erreur"] == 0

        ref = db_session.query(Reference).filter(Reference.code == "A001").first()
        assert ref is not None
        assert ref.stock_actuel == 50.0
        assert ref.prix_cession == 550.0

        # CMM = 1200 / 12 = 100, la seule valeur dérivable d'un total unique
        assert ref.cmm == 100.0

        # Jamais inventés à partir d'un total global
        assert ref.cmmax is None
        assert ref.sigma is None
        assert ref.ss is None
        assert ref.pc is None
        assert ref.statut is None
        assert ref.qte_a_commander is None
        assert ref.classe is None
        assert ref.fsn is None

        # Aucune ligne de vente mensuelle créée par cet import (pas de détail mensuel réel)
        ventes = db_session.query(VenteMensuelle).filter(VenteMensuelle.reference_id == ref.id).all()
        assert len(ventes) == 0

    def test_stock_actuel_inclut_la_reserve(self, client, token, db_session):
        """Section 4bis (V9) : stock actuel total = Qté Sal. + Réserve."""
        headers = {"Authorization": f"Bearer {token}"}
        client.post(
            "/api/v1/imports/historique-logpharma-annuel",
            files={"file": ("annuel.xlsx", _fichier_logpharma(stock=50, reserve=8, sorties=1200), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=headers,
        )
        ref = db_session.query(Reference).filter(Reference.code == "A001").first()
        assert ref.stock_actuel == 58.0  # 50 (Qté Sal.) + 8 (Réserve)

    def test_sorties_negatives_donnent_cmm_zero(self, client, token, db_session):
        headers = {"Authorization": f"Bearer {token}"}
        client.post(
            "/api/v1/imports/historique-logpharma-annuel",
            files={"file": ("annuel.xlsx", _fichier_logpharma(sorties=-500), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=headers,
        )
        ref = db_session.query(Reference).filter(Reference.code == "A001").first()
        assert ref.cmm == 0.0

    def test_reference_sans_statut_absente_de_la_liste_daction(self, client, token, db_session):
        """Une référence sans historique mensuel complet ne doit jamais apparaître comme actionnable."""
        headers = {"Authorization": f"Bearer {token}"}
        client.post(
            "/api/v1/imports/historique-logpharma-annuel",
            files={"file": ("annuel.xlsx", _fichier_logpharma(stock=0, sorties=1200), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=headers,
        )
        response = client.get("/api/v1/dashboard/liste-action", headers=headers)
        assert response.status_code == 200
        codes = [l["code"] for l in response.json()]
        assert "A001" not in codes
