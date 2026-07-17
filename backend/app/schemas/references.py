from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

VED_VALEURS_AUTORISEES = {"Vital", "Essentiel", "Désirable", None}
INCLUSION_MANUELLE_VALEURS_AUTORISEES = {"inclure", "exclure", None}


class ReferenceOut(BaseModel):
    id: UUID
    code: str
    designation: str
    forme: Optional[str]
    prix_cession: Optional[float]
    classe: Optional[str]
    ved: Optional[str]
    fsn: Optional[str]
    stock_actuel: float
    cmm: Optional[float]
    ss: Optional[float]
    pc: Optional[float]
    statut: Optional[str]
    qte_a_commander: Optional[float]
    qte_a_commander_override: Optional[float]
    inclusion_manuelle: Optional[str]
    risque_fournisseur_jours: int
    couverture_jours: Optional[float]
    tresorerie_liberee: Optional[float]

    model_config = {"from_attributes": True}


class AjustementCommandeUpdate(BaseModel):
    """Section 6.7 : arbitrage manuel du pharmacien sur une référence donnée."""
    qte_a_commander_override: Optional[float] = Field(default=None, ge=0)
    inclusion_manuelle: Optional[str] = None

    @field_validator("inclusion_manuelle")
    @classmethod
    def valider_inclusion(cls, v):
        if v not in INCLUSION_MANUELLE_VALEURS_AUTORISEES:
            raise ValueError("inclusion_manuelle doit être 'inclure', 'exclure' ou null.")
        return v


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
