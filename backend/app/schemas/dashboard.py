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
    sorties_derniere_commande: Optional[float]  # vendu depuis le dernier import de commande (Type 2)
    statut: str
    qte_a_commander: float
    qte_a_commander_auto: float           # suggestion brute du moteur, avant arbitrage
    qte_a_commander_override: Optional[float]  # quantité saisie manuellement par le pharmacien, si renseignée
    inclusion_manuelle: Optional[str]     # "inclure" / "exclure" / null
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


class LignePlafondOut(BaseModel):
    id: str
    code: str
    designation: str
    classe: Optional[str]
    statut: str
    ved: Optional[str]
    stock_actuel: float
    qte_a_commander: float
    qte_a_commander_auto: float
    qte_a_commander_override: Optional[float]
    inclusion_manuelle: Optional[str]
    valeur_fcfa: float
    hors_plafond: bool

    model_config = {"from_attributes": False}


class CommandePlafonneeOut(BaseModel):
    plafond: Optional[float]
    sans_restriction: bool
    budget_utilise: float
    hors_plafond: list[LignePlafondOut]
    inclus: list[LignePlafondOut]
    reporte: list[LignePlafondOut]
    montant_reporte: float
    rupture_non_vitale_reportee: bool

    model_config = {"from_attributes": False}


class AlerteStrategiqueOut(BaseModel):
    id: str
    code: str
    designation: str
    classe: Optional[str]
    statut: str                    # RUPTURE / CRITIQUE
    jours_rupture: int             # estimé, arrondi à l'entier supérieur
    ventes_perdues_fcfa: float     # estimé — (CMM/30) x jours_rupture x prix_public

    model_config = {"from_attributes": False}


class AlertesStrategiquesOut(BaseModel):
    references: list[AlerteStrategiqueOut]
    nb_references: int
    ventes_perdues_totales_fcfa: float

    model_config = {"from_attributes": False}
