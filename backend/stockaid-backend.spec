# -*- mode: python ; coding: utf-8 -*-
"""
Build PyInstaller du backend StockAid, en mode onedir (démarrage plus rapide
et plus simple à déboguer qu'un onefile). Cible : run.py.

hiddenimports explicites pour les libs à imports dynamiques/lazy que
PyInstaller ne détecte pas toujours par analyse statique :
- reportlab.* : importé à l'intérieur d'une fonction dans export_dashboard.py
- pandas/numpy/scipy/openpyxl : moteur de calcul et parsing des imports
- jose, passlib/bcrypt, email_validator : auth et validation
- dialectes sqlalchemy : requis même pour SQLite seul selon la version
- alembic/mako : migrations de schéma exécutées au démarrage (run.py)

datas : alembic.ini + le dossier alembic/ (env.py, script.py.mako, versions/)
doivent être présents à côté de l'exe pour que les migrations tournent une
fois packagé — PyInstaller ne les embarque pas automatiquement puisqu'ils
ne sont référencés que par chemin de fichier, jamais par un `import`.
"""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# reportlab a besoin de ses fichiers de métriques de polices (Helvetica,
# Times...) sous reportlab/fonts/*.afm — ce sont des données, pas du code
# Python, donc collect_submodules ne les embarque pas : sans ça, la
# génération de PDF plante au premier appel une fois packagé (marchait en
# dev car ces fichiers sont lus directement depuis le venv).
datas = collect_data_files("reportlab")

hiddenimports = (
    collect_submodules("reportlab")
    + collect_submodules("pandas")
    + collect_submodules("scipy")
    + collect_submodules("openpyxl")
    + collect_submodules("sqlalchemy.dialects")
    + collect_submodules("alembic")
    + collect_submodules("mako")
    + [
        "passlib.handlers.bcrypt",
        "bcrypt",
        "jose",
        "jose.backends.cryptography_backend",
        "email_validator",
        "multipart",
    ]
)

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=datas + [
        ("alembic.ini", "."),
        ("alembic", "alembic"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="stockaid-backend",
    debug=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="stockaid-backend",
)
