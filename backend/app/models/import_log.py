from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, Uuid
from app.models.base import BaseModel


class ImportLog(BaseModel):
    """
    Journal de chaque import réalisé par une officine.
    """
    __tablename__ = "import_logs"

    officine_id      = Column(Uuid(as_uuid=True), ForeignKey("officines.id", ondelete="CASCADE"), nullable=False, index=True)
    nom_fichier      = Column(String, nullable=False)
    statut           = Column(String, nullable=False, default="en_cours")  # en_cours / succes / erreur
    nb_lignes_total  = Column(Integer, nullable=True)
    nb_lignes_ok     = Column(Integer, nullable=True)
    nb_lignes_erreur = Column(Integer, nullable=True)
    erreurs_detail   = Column(Text, nullable=True)   # JSON des erreurs par ligne
    sorties_totales  = Column(Float, nullable=True)  # import de commande (Type 2) uniquement : somme des sorties de la période
