from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes.auth import router as auth_router

app = FastAPI(
    title=settings.APP_NAME,
    description="SaaS d'aide à la décision pour la gestion des stocks en pharmacie",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuration CORS (pour que le frontend React puisse parler au backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enregistrement des routes
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)

@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l'API SAD OFFICINE"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}