from sqlalchemy import Column, String, Integer, ForeignKey, Uuid, UniqueConstraint
from app.models.base import BaseModel


class DelaiCircuit(BaseModel):
    """
    Délai fournisseur (moyen/max) spécifique à un circuit d'approvisionnement
    (local / France / Chine-Inde...) pour une officine. Une référence sans
    circuit connu, ou dont le circuit n'a pas été configuré ici, retombe sur
    le délai global de ParametreOfficine (section 5/8 du cahier des charges).
    """
    __tablename__ = "delais_circuit"
    __table_args__ = (UniqueConstraint("officine_id", "circuit", name="uq_delai_circuit_officine"),)

    officine_id = Column(Uuid(as_uuid=True), ForeignKey("officines.id", ondelete="CASCADE"), nullable=False, index=True)
    circuit = Column(String, nullable=False)
    dl_moy_jours = Column(Integer, nullable=False)
    dl_max_jours = Column(Integer, nullable=False)
