from sqlalchemy import Column, String
from app.models.base import BaseModel

class Officine(BaseModel):
    __tablename__ = "officines"

    nom = Column(String, index=True, nullable=False)
    # On ajoutera adresse, téléphone, etc. plus tard