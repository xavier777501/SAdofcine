"""
Garde-fou global : les tests ne doivent JAMAIS toucher la vraie base de dev.

Certains tests (test_isolation.py) font Base.metadata.create_all/drop_all sur
le moteur configuré — sans ça, ils s'exécutent contre sad_officine.db et la
vident intégralement à chaque run. On force donc DATABASE_URL vers un fichier
dédié aux tests AVANT que app.core.config / app.core.database ne soient
importés par quoi que ce soit (conftest.py est chargé par pytest avant toute
collecte de test).
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_sad_officine.db"

import pytest

from app.core.config import settings

assert "test_sad_officine" in settings.DATABASE_URL, (
    "Les tests pointent vers la vraie base de dev, pas vers une base de test ! "
    f"DATABASE_URL={settings.DATABASE_URL}"
)


@pytest.fixture(scope="session", autouse=True)
def _nettoyer_base_de_test():
    """Supprime le fichier de base de test à la fin de la session pytest."""
    yield
    from app.core.database import engine
    engine.dispose()  # ferme les connexions du pool (sinon Windows verrouille le fichier)
    chemin = "test_sad_officine.db"
    if os.path.exists(chemin):
        try:
            os.remove(chemin)
        except PermissionError:
            pass  # fichier encore verrouillé par un autre process ; sans gravité, ignoré au prochain run
