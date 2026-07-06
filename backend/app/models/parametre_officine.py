from sqlalchemy import Column, Float, Integer, ForeignKey, Uuid
from app.models.base import BaseModel


class ParametreOfficine(BaseModel):
    """
    Paramètres globaux de l'officine utilisés par le moteur SAD.
    Créés automatiquement avec des valeurs par défaut au premier import.
    Modifiables via Epic C (page Réglages).
    """
    __tablename__ = "parametres_officine"

    officine_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("officines.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Délais fournisseurs (jours) — affinés par circuit en Epic C
    dl_moy_jours = Column(Integer, nullable=False, default=7)
    dl_max_jours = Column(Integer, nullable=False, default=15)

    # Cycle de commande T (jours) : 0=continu, 10=décade, 30=mensuel
    cycle_commande_jours = Column(Integer, nullable=False, default=10)

    # Paramètres EOQ
    cout_commande = Column(Float, nullable=False, default=5000.0)   # FCFA par commande
    taux_detention = Column(Float, nullable=False, default=0.20)    # 20 % annuel
