import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Uuid
from app.core.database import Base


class BaseModel(Base):
    __abstract__ = True

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)