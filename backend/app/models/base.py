"""
Modèle de base commun avec UUID et timestamps.
Utilise le Base de app.core.database pour être cohérent avec Alembic.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base  # ← IMPORTANT : importe le Base de database.py


class BaseModel(Base):
    """
    Classe de base abstraite pour tous les modèles.
    """
    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)