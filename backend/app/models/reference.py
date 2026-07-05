from sqlalchemy import Column, String, Float, Integer, Boolean, ForeignKey, Uuid
from app.models.base import BaseModel


class Reference(BaseModel):
    """
    Une référence produit appartenant à une officine.
    Alimentée à chaque import, recalculée par le moteur SAD.
    """
    __tablename__ = "references"

    officine_id = Column(Uuid(as_uuid=True), ForeignKey("officines.id", ondelete="CASCADE"), nullable=False, index=True)

    # --- Champs issus de l'import ---
    code        = Column(String, nullable=False, index=True)
    designation = Column(String, nullable=False)
    forme       = Column(String, nullable=True)
    prix_cession = Column(Float, nullable=True)   # FCFA
    prix_public  = Column(Float, nullable=True)   # FCFA
    stock_actuel = Column(Float, nullable=False, default=0)
    circuit      = Column(String, nullable=True)  # local / France / Chine-Inde...

    # --- Saisie manuelle par le pharmacien ---
    ved              = Column(String, nullable=True)   # Vital / Essentiel / Désirable / None
    risque_fournisseur_jours = Column(Integer, nullable=False, default=0)

    # --- Résultats moteur SAD (calculés, jamais saisis) ---
    classe     = Column(String, nullable=True)    # A / B / C
    fsn        = Column(String, nullable=True)    # Fast / Slow / Non-moving
    cmm        = Column(Float, nullable=True)
    cmmax      = Column(Float, nullable=True)
    sigma      = Column(Float, nullable=True)     # écart-type mensuel
    z_service  = Column(Float, nullable=True)     # facteur Z selon VED
    ss         = Column(Float, nullable=True)     # stock de sécurité continu
    pc         = Column(Float, nullable=True)     # point de commande continu
    eoq        = Column(Float, nullable=True)     # quantité économique (indicatif)
    ss_periodique     = Column(Float, nullable=True)
    niveau_recompletement = Column(Float, nullable=True)  # S
    qte_a_commander  = Column(Float, nullable=True)       # quantité finale (cycle)
    qte_commander_continu = Column(Float, nullable=True)  # quantité finale (continu)
    statut     = Column(String, nullable=True)    # RUPTURE / CRITIQUE / COMMANDER / OK
    couverture_jours = Column(Float, nullable=True)
    tresorerie_liberee = Column(Float, nullable=True)
