from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import BaseModel

class User(BaseModel):
    __tablename__ = "users"

    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # ISOLATION STRICTE : Chaque utilisateur est lié à UNE officine
    officine_id = Column(UUID(as_uuid=True), ForeignKey("officines.id", ondelete="CASCADE"), nullable=False)