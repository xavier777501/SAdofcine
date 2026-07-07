from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l'API SAD OFFICINE"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}