from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

VED_VALEURS_AUTORISEES = {"Vital", "Essentiel", "Désirable", None}


class ReferenceOut(BaseModel):
    id: UUID
    code: str
    designation: str
    classe: Optional[str]
    ved: Optional[str]
    fsn: Optional[str]
    stock_actuel: float
    statut: Optional[str]
    qte_a_commander: Optional[float]
    qte_commander_continu: Optional[float]
    risque_fournisseur_jours: int
    couverture_jours: Optional[float]
    tresorerie_liberee: Optional[float]

    model_config = {"from_attributes": True}


class VedUpdate(BaseModel):
    ved: Optional[str] = None

    @field_validator("ved")
    @classmethod
    def valider_ved(cls, v):
        if v not in VED_VALEURS_AUTORISEES:
            raise ValueError("ved doit être 'Vital', 'Essentiel', 'Désirable' ou null.")
        return v


class RisqueFournisseurUpdate(BaseModel):
    risque_fournisseur_jours: int = Field(ge=0)
