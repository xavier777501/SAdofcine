from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


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
    notification_active: bool
    notification_heure: str
    notification_email: Optional[str]

    model_config = {"from_attributes": True}


class ParametreOfficineUpdate(BaseModel):
    dl_moy_jours: Optional[int] = Field(default=None, gt=0)
    dl_max_jours: Optional[int] = Field(default=None, gt=0)
    # Rythmes couverts par la formule périodique du cahier des charges
    # (section 6.5) : celle-ci est générique en T (jours entre deux
    # commandes) — 1=journalière, 10=décade, 30=mensuel sont juste les
    # valeurs usuelles, pas des cas particuliers de la formule.
    cycle_commande_jours: Optional[Literal[1, 10, 30]] = Field(default=None)
    cout_commande: Optional[float] = Field(default=None, gt=0)
    taux_detention: Optional[float] = Field(default=None, gt=0, lt=1)
    niveau_service_vital: Optional[float] = Field(default=None, gt=0, lt=1)
    niveau_service_essentiel: Optional[float] = Field(default=None, gt=0, lt=1)
    niveau_service_desirable: Optional[float] = Field(default=None, gt=0, lt=1)
    niveau_service_non_renseigne: Optional[float] = Field(default=None, gt=0, lt=1)
    # Optionnel : vide/absent = pas de plafond (section 6.7). Peut être remis à
    # None explicitement pour désactiver le plafond une fois configuré.
    plafond_commande_fcfa: Optional[float] = Field(default=None, ge=0)
    # Notification quotidienne par e-mail (section 7.2) — envoi opportuniste,
    # voir app/services/notification_quotidienne.py.
    notification_active: Optional[bool] = None
    notification_heure: Optional[str] = None
    notification_email: Optional[str] = None

    @field_validator("notification_heure")
    @classmethod
    def valider_heure(cls, v):
        if v is None:
            return v
        try:
            h, m = v.split(":")
            if not (0 <= int(h) <= 23 and 0 <= int(m) <= 59):
                raise ValueError
        except (ValueError, AttributeError):
            raise ValueError("notification_heure doit être au format HH:MM.")
        return v
