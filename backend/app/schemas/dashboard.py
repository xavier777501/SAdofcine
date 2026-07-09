from pydantic import BaseModel
from typing import Optional


class KpisOut(BaseModel):
    nb_references: int             # total de références
    nb_rupture: int
    nb_critique: int
    nb_commander: int              # statut COMMANDER uniquement
    nb_a_commander: int            # rupture + critique + commander (total actionnable)
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
    cmm: float                    # consommation mensuelle moyenne (ventes/mois)
    vente_m1: float                # ventes réelles du mois le plus récent (M-1)
    statut: str
    qte_a_commander: float
    valeur_fcfa: float            # qte_a_commander × prix_cession
    texte_decision: str

    model_config = {"from_attributes": False}


class VenteM1Out(BaseModel):
    code: str
    designation: str
    vente_m1: float                # quantité vendue le mois dernier
    stock_actuel: float
    statut: str                    # RUPTURE / CRITIQUE / COMMANDER / OK
    qte_a_commander: float

    model_config = {"from_attributes": False}


class LigneNePasCommanderOut(BaseModel):
    code: str
    designation: str
    stock_actuel: float
    tresorerie_immobilisee: float   # FCFA dormant sur cette référence
    motif: str                      # texte clair, sans jargon

    model_config = {"from_attributes": False}
