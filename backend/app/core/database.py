from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.core.config import settings

# Configuration du moteur SQL (optimisé pour la prod)
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,      # Vérifie que la connexion est alive avant chaque requête
    pool_size=10,            # Nombre de connexions gardées ouvertes
    max_overflow=20,         # Connexions supplémentaires en cas de pic
    pool_recycle=3600,       # Recycle les connexions après 1h (évite les coupures BDD)
    echo=settings.DEBUG,     # Affiche les requêtes SQL dans la console si DEBUG=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """Dépendance FastAPI pour injecter la session BDD."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()