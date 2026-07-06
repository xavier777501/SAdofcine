from typing import Optional
from pydantic import BaseModel, Field


class ParametreOfficineOut(BaseModel):
    dl_moy_jours: int
    dl_max_jours: int
    cycle_commande_jours: int
    cout_commande: float
    taux_detention: float

    model_config = {"from_attributes": True}


class ParametreOfficineUpdate(BaseModel):
    dl_moy_jours: Optional[int] = Field(default=None, gt=0)
    dl_max_jours: Optional[int] = Field(default=None, gt=0)
    cycle_commande_jours: Optional[int] = Field(default=None, ge=0)
    cout_commande: Optional[float] = Field(default=None, gt=0)
    taux_detention: Optional[float] = Field(default=None, gt=0, lt=1)
