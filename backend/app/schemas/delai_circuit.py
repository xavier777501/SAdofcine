from pydantic import BaseModel, Field


class DelaiCircuitOut(BaseModel):
    circuit: str
    dl_moy_jours: int
    dl_max_jours: int
    configure: bool  # False = valeurs de repli (délai global), pas encore personnalisé

    model_config = {"from_attributes": True}


class DelaiCircuitUpdate(BaseModel):
    dl_moy_jours: int = Field(gt=0)
    dl_max_jours: int = Field(gt=0)
