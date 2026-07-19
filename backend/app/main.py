import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import Base, engine
from app.api.routes.auth import router as auth_router
from app.api.routes.imports import router as imports_router
from app.api.routes.calcul import router as calcul_router
from app.api.routes.parametres import router as parametres_router
from app.api.routes.references import router as references_router
from app.api.routes.dashboard import router as dashboard_router
import app.models.officine           # noqa: F401
import app.models.user               # noqa: F401
import app.models.reference          # noqa: F401
import app.models.vente_mensuelle    # noqa: F401
import app.models.import_log         # noqa: F401
import app.models.column_mapping     # noqa: F401
import app.models.parametre_officine # noqa: F401
import app.models.password_reset_token # noqa: F401
import app.models.delai_circuit      # noqa: F401

app = FastAPI(
    title=settings.APP_NAME,
    description="SaaS d'aide à la décision pour la gestion des stocks en pharmacie",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    # Crée les tables automatiquement au démarrage (SQLite local, pas besoin d'alembic upgrade)
    Base.metadata.create_all(bind=engine)

app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(imports_router, prefix=settings.API_V1_PREFIX)
app.include_router(calcul_router, prefix=settings.API_V1_PREFIX)
app.include_router(parametres_router, prefix=settings.API_V1_PREFIX)
app.include_router(references_router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard_router, prefix=settings.API_V1_PREFIX)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# ── Mode desktop (Electron) : sert le frontend build à la place de la page
# JSON de dev — STOCKAID_FRONTEND_DIR n'est positionné que par l'app packagée,
# jamais en développement (uvicorn + Vite séparés sur des ports différents).
_frontend_dir = os.environ.get("STOCKAID_FRONTEND_DIR")

if _frontend_dir and Path(_frontend_dir).is_dir():
    _frontend_path = Path(_frontend_dir)
    _assets_dir = _frontend_path / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        """Sert un fichier statique existant (favicon, etc.), sinon index.html
        pour laisser react-router gérer la route côté client (SPA)."""
        candidate = _frontend_path / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_frontend_path / "index.html")
else:
    @app.get("/")
    def read_root():
        return {"message": "Bienvenue sur l'API SAD OFFICINE"}