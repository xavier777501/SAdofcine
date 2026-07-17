from typing import Literal, Optional
from pydantic import BaseModel, Field


class ParametreOfficineOut(BaseModel):
    dl_moy_jours: int
    dl_max_jours: int
    cycle_commande_jours: int
    cout_commande: float
    taux_detention: float
    niveau_service_vital: float
    niveau_service_essentiel: float
    niveau_service_desirable: float
    niveau_service_non_renseigne: float
    plafond_commande_fcfa: Optional[float]

    model_config = {"from_attributes": True}


class ParametreOfficineUpdate(BaseModel):
    dl_moy_jours: Optional[int] = Field(default=None, gt=0)
    dl_max_jours: Optional[int] = Field(default=None, gt=0)
    # Seuls rythmes définis au cahier des charges (section 6.5) : décade ou mensuel.
    cycle_commande_jours: Optional[Literal[10, 30]] = Field(default=None)
    cout_commande: Optional[float] = Field(default=None, gt=0)
    taux_detention: Optional[float] = Field(default=None, gt=0, lt=1)
    niveau_service_vital: Optional[float] = Field(default=None, gt=0, lt=1)
    niveau_service_essentiel: Optional[float] = Field(default=None, gt=0, lt=1)
    niveau_service_desirable: Optional[float] = Field(default=None, gt=0, lt=1)
    niveau_service_non_renseigne: Optional[float] = Field(default=None, gt=0, lt=1)
    # Optionnel : vide/absent = pas de plafond (section 6.7). Peut être remis à
    # None explicitement pour désactiver le plafond une fois configuré.
    plafond_commande_fcfa: Optional[float] = Field(default=None, ge=0)
