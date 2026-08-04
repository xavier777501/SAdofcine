from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.core.config import settings

# SQLite requiert check_same_thread=False pour fonctionner avec FastAPI (multi-thread)
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG,
    # pool_pre_ping : évite les erreurs "SSL connection has been closed
    # unexpectedly" quand la base Postgres managée (Supabase/Neon/RDS...)
    # coupe les connexions inactives — sans impact sur SQLite.
    pool_pre_ping=True,
)

if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _):
        # WAL : les lectures ne bloquent plus les écritures (et inversement),
        # journal plus résistant qu'un rollback journal classique en cas de
        # coupure. busy_timeout évite une erreur immédiate "database is
        # locked" si deux requêtes se chevauchent brièvement.
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """Dépendance FastAPI pour injecter la session BDD."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()