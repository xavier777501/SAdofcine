from sqlalchemy import Column, String, ForeignKey, Uuid
from app.models.base import BaseModel


class ColumnMapping(BaseModel):
    """
    Mappage sauvegardé entre les colonnes du fichier d'export et les champs SAD.
    Une ligne par champ cible, par officine.
    """
    __tablename__ = "column_mappings"

    officine_id    = Column(Uuid(as_uuid=True), ForeignKey("officines.id", ondelete="CASCADE"), nullable=False, index=True)
    champ_cible    = Column(String, nullable=False)   # ex: "code", "stock_actuel", "vente_m1"
    colonne_source = Column(String, nullable=False)   # nom de colonne tel qu'il apparaît dans le fichier
