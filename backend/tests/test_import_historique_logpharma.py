"""
Vérifie l'import Type 1 (historique), mécanisme glissant conforme au cahier
des charges (section 4bis) : "à chaque import, le mois le plus ancien sort de
l'historique et le nouveau mois entre" — Logpharma ne fournissant qu'un total
de sorties par période, chaque import représente automatiquement le nouveau
mois le plus récent, sans que le pharmacien ait à préciser lequel.
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


def _fichier_logpharma(code="A001", designation="Doliprane 500mg", stock=50, sorties=100,
                       prix_cession=550, prix_public=900):
    """Même format fixe 'Listing de Produit à Commander' que le Type 2 (section 4bis)."""
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


def _importer(client, headers, **kwargs):
    return client.post(
        "/api/v1/imports/historique-logpharma",
        files={"file": ("mois.xlsx", _fichier_logpharma(**kwargs), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=headers,
    )


class TestImportHistoriqueLogpharmaGlissant:
    def test_premier_import_cree_la_reference_en_mois_1(self, client, token, db_session):
        headers = {"Authorization": f"Bearer {token}"}
        response = _importer(client, headers, stock=50, sorties=120)
        assert response.status_code == 200
        body = response.json()
        assert body["nb_lignes_ok"] == 1
        assert body["nb_lignes_erreur"] == 0

        ref = db_session.query(Reference).filter(Reference.code == "A001").first()
        assert ref is not None
        assert ref.stock_actuel == 50.0
        assert ref.prix_cession == 550.0

        ventes = db_session.query(VenteMensuelle).filter(VenteMensuelle.reference_id == ref.id).all()
        assert len(ventes) == 1
        assert ventes[0].mois_index == 1
        assert ventes[0].quantite == 120.0
        assert ref.cmm == 10.0  # 120 / 12

    def test_deuxieme_import_decale_lancien_mois_et_met_a_jour_le_stock(self, client, token, db_session):
        headers = {"Authorization": f"Bearer {token}"}
        _importer(client, headers, stock=50, sorties=120)
        response = _importer(client, headers, stock=80, sorties=60)
        assert response.status_code == 200

        ref = db_session.query(Reference).filter(Reference.code == "A001").first()
        # Le stock reflète toujours le dernier import, quel qu'il soit
        assert ref.stock_actuel == 80.0

        ventes = db_session.query(VenteMensuelle).filter(
            VenteMensuelle.reference_id == ref.id
        ).order_by(VenteMensuelle.mois_index).all()
        assert len(ventes) == 2
        assert [(v.mois_index, v.quantite) for v in ventes] == [(1, 60.0), (2, 120.0)]
        assert ref.cmm == 15.0  # (60 + 120) / 12

    def test_treizieme_import_fait_sortir_le_plus_ancien(self, client, token, db_session):
        headers = {"Authorization": f"Bearer {token}"}
        for i in range(13):
            _importer(client, headers, sorties=(i + 1) * 10)

        ref = db_session.query(Reference).filter(Reference.code == "A001").first()
        ventes = db_session.query(VenteMensuelle).filter(
            VenteMensuelle.reference_id == ref.id
        ).order_by(VenteMensuelle.mois_index).all()

        # Jamais plus de 12 mois d'historique, même après 13 imports
        assert len(ventes) == 12
        # Le plus récent (mois_index=1) est le tout dernier import (i=12 -> 130)
        assert ventes[0].mois_index == 1
        assert ventes[0].quantite == 130.0
        # Le plus ancien restant (mois_index=12) est le 2e import (i=1 -> 20) :
        # le tout premier import (i=0 -> 10) est bien sorti de l'historique.
        assert ventes[-1].mois_index == 12
        assert ventes[-1].quantite == 20.0

    def test_sorties_negatives_mises_a_zero(self, client, token, db_session):
        headers = {"Authorization": f"Bearer {token}"}
        _importer(client, headers, sorties=-15)
        ref = db_session.query(Reference).filter(Reference.code == "A001").first()
        vente = db_session.query(VenteMensuelle).filter(VenteMensuelle.reference_id == ref.id).first()
        assert vente.quantite == 0.0

    def test_nouvelle_reference_sans_designation_en_erreur(self, client, token):
        headers = {"Authorization": f"Bearer {token}"}
        response = _importer(client, headers, code="INCONNU", designation=None)
        assert response.status_code == 200
        body = response.json()
        assert body["nb_lignes_erreur"] == 1
