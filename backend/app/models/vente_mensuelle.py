from sqlalchemy import Column, Float, Integer, ForeignKey, Uuid
from app.models.base import BaseModel


class VenteMensuelle(BaseModel):
    """
    Historique des ventes mensuelles par référence.
    12 lignes max par référence (mois_index 1=le plus récent, 12=le plus ancien).
    """
    __tablename__ = "ventes_mensuelles"

    reference_id = Column(Uuid(as_uuid=True), ForeignKey("references.id", ondelete="CASCADE"), nullable=False, index=True)
    mois_index   = Column(Integer, nullable=False)  # 1 = mois le plus récent
    quantite     = Column(Float, nullable=False, default=0)
