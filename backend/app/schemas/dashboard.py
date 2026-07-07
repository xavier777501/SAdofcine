from pydantic import BaseModel
from typing import Optional


class KpisOut(BaseModel):
    nb_rupture: int
    nb_critique: int
    nb_a_commander: int           # rupture + critique + commander
    valeur_commande_fcfa: float   # sum(qte_a_commander × prix_cession)
    tresorerie_liberee_fcfa: float


class LigneActionOut(BaseModel):
    id: str
    code: str
    designation: str
    classe: Optional[str]
    fsn: Optional[str]
    ved: Optional[str]
    stock_actuel: float
    statut: str
    qte_a_commander: float
    valeur_fcfa: float            # qte_a_commander × prix_cession
    texte_decision: str

    model_config = {"from_attributes": False}
