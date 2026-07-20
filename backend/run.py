"""Point d'entrée pour le build PyInstaller (exécutable desktop).

Contrairement à `uvicorn app.main:app` (utilisé en dev), ce script :
1. Sauvegarde la base existante avant toute migration (sécurité en cas de
   problème pendant la mise à jour de schéma).
2. Applique les migrations Alembic (`upgrade head`) — sur une base neuve,
   ça la crée entièrement depuis zéro ; sur une base d'une version
   précédente de l'app, ça applique uniquement ce qui manque. C'est la
   différence avec `Base.metadata.create_all()` (utilisé par ailleurs au
   démarrage FastAPI) qui ne crée que les tables absentes et ne modifie
   jamais une table déjà existante — insuffisant pour une mise à jour.
3. Démarre le serveur.
"""
import glob
import os
import shutil
import sys
from datetime import datetime

import uvicorn

NB_BACKUPS_CONSERVES = 5


def _base_dir() -> str:
    """Dossier contenant alembic.ini/alembic/ — celui de l'exe une fois
    packagé (PyInstaller onedir place les données à côté de l'exe, pas dans
    un dossier temporaire), celui du fichier source en dev."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def _sqlite_path_from_url(database_url: str) -> str | None:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return None
    return database_url[len(prefix):]


def _checkpoint_wal(db_path: str) -> None:
    """
    En mode WAL, les écritures récentes peuvent rester dans le fichier
    compagnon `<db>-wal` tant que la connexion n'a pas été fermée
    proprement (ex. app fermée brutalement, plantage) — le fichier
    principal seul serait alors incomplet. On force ici tout le contenu du
    WAL dans le fichier principal avant de le copier, pour qu'une sauvegarde
    du seul fichier .db suffise à tout restaurer.
    """
    import sqlite3
    try:
        con = sqlite3.connect(db_path, timeout=5)
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        con.close()
    except sqlite3.Error:
        pass  # tentative sur une base verrouillée/corrompue : on sauvegarde quand même en l'état


def _sauvegarder_base(db_path: str) -> None:
    if not os.path.isfile(db_path):
        return  # première installation, rien à sauvegarder

    _checkpoint_wal(db_path)

    backups_dir = os.path.join(os.path.dirname(db_path), "backups")
    os.makedirs(backups_dir, exist_ok=True)

    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    nom_fichier = os.path.basename(db_path)
    destination = os.path.join(backups_dir, f"{nom_fichier}.{horodatage}.bak")
    shutil.copy2(db_path, destination)

    # Ne garde que les N sauvegardes les plus récentes.
    sauvegardes = sorted(glob.glob(os.path.join(backups_dir, f"{nom_fichier}.*.bak")))
    for ancienne in sauvegardes[:-NB_BACKUPS_CONSERVES]:
        os.remove(ancienne)


def _base_deja_initialisee_sans_alembic(db_path: str) -> bool:
    """
    Vrai si le fichier existe, contient déjà les tables de l'app, mais n'a
    jamais été suivi par Alembic — cas d'une base créée par une version
    antérieure de l'exe desktop (avant l'ajout des migrations), via
    `Base.metadata.create_all()` au démarrage FastAPI. Dans ce cas précis
    (et uniquement celui-ci) le schéma correspond déjà à la définition
    courante des modèles, donc à "head" : il faut le marquer comme tel
    (`stamp`) plutôt que de rejouer les migrations de création, qui
    échoueraient sur des tables déjà présentes.
    """
    if not os.path.isfile(db_path):
        return False
    import sqlite3
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name IN ('officines', 'alembic_version')"
        )
        noms = {row[0] for row in cur.fetchall()}
        return "officines" in noms and "alembic_version" not in noms
    finally:
        con.close()


def _appliquer_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    from app.core.config import settings

    db_path = _sqlite_path_from_url(settings.DATABASE_URL)
    if db_path:
        _sauvegarder_base(db_path)

    base_dir = _base_dir()
    cfg = Config(os.path.join(base_dir, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(base_dir, "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

    if db_path and _base_deja_initialisee_sans_alembic(db_path):
        command.stamp(cfg, "head")
    else:
        command.upgrade(cfg, "head")


if __name__ == "__main__":
    _appliquer_migrations()

    from app.main import app

    uvicorn.run(app, host="127.0.0.1", port=8000)
