"""
Vérifie que l'import historique par mappage (POST /imports/mapping puis
POST /imports/) fonctionne toujours correctement — alternative au format fixe
Logpharma pour une pharmacie dont l'export a un format différent (section 9,
"import tolérant" : mappage de colonnes configurable).
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


def _fichier_avec_colonnes_custom():
    """Un fichier avec un format 'maison' (noms de colonnes non standards)."""
    df = pd.DataFrame([
        {
            "CodeArticle": "A001", "Libelle": "Doliprane 500mg", "StockDispo": 50,
            "M1": 10, "M2": 12, "M3": 8, "M4": 9, "M5": 11, "M6": 10,
            "M7": 9, "M8": 8, "M9": 10, "M10": 12, "M11": 11, "M12": 9,
        }
    ])
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    return buf


class TestImportMappage:
    def test_mappage_puis_import_calcule_correctement(self, client, token, db_session):
        headers = {"Authorization": f"Bearer {token}"}

        # 1) Aperçu du fichier
        preview = client.post(
            "/api/v1/imports/preview",
            files={"file": ("historique.xlsx", _fichier_avec_colonnes_custom(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=headers,
        )
        assert preview.status_code == 200
        colonnes = preview.json()["colonnes"]
        assert "CodeArticle" in colonnes

        # 2) Sauvegarde du mappage
        mapping = {
            "champ_cible": "code", "colonne_source": "CodeArticle",
        }
        payload = {"mapping": [
            {"champ_cible": "code", "colonne_source": "CodeArticle"},
            {"champ_cible": "designation", "colonne_source": "Libelle"},
            {"champ_cible": "stock_actuel", "colonne_source": "StockDispo"},
        ] + [{"champ_cible": f"vente_m{i}", "colonne_source": f"M{i}"} for i in range(1, 13)]}
        save = client.post("/api/v1/imports/mapping", json=payload, headers=headers)
        assert save.status_code == 200

        # 3) Import réel
        response = client.post(
            "/api/v1/imports/",
            files={"file": ("historique.xlsx", _fichier_avec_colonnes_custom(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["nb_lignes_ok"] == 1
        assert body["nb_lignes_erreur"] == 0

        ref = db_session.query(Reference).filter(Reference.code == "A001").first()
        assert ref is not None
        assert ref.designation == "Doliprane 500mg"
        assert ref.stock_actuel == 50.0
        # CMM = (10+12+8+9+11+10+9+8+10+12+11+9)/12 = 119/12, arrondi à 1 décimale
        assert ref.cmm == round(119 / 12, 1)

        ventes = db_session.query(VenteMensuelle).filter(VenteMensuelle.reference_id == ref.id).all()
        assert len(ventes) == 12

    def test_mappage_reste_isole_du_format_fixe_commande(self, client, token, db_session):
        """Le mappage sauvegardé pour l'import historique ne doit jamais affecter l'import commande (format fixe, indépendant)."""
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"mapping": [{"champ_cible": "code", "colonne_source": "CodeArticle"}]}
        save = client.post("/api/v1/imports/mapping", json=payload, headers=headers)
        assert save.status_code == 200

        # L'import de commande ne dépend d'aucun mappage sauvegardé — doit
        # continuer à fonctionner sans configuration supplémentaire.
        response = client.get("/api/v1/imports/mapping", headers=headers)
        assert response.json()["mapping"]["code"] == "CodeArticle"
