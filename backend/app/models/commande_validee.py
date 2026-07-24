from sqlalchemy import Column, String, Text, ForeignKey, Uuid
from app.models.base import BaseModel


class CommandeValidee(BaseModel):
    """
    Traçabilité des commandes — section 7.3 du cahier des charges V9.
    Un instantané de la liste d'action est enregistré à chaque export
    (PDF/Excel), moment où le pharmacien consulte la liste avant de passer
    sa commande chez le grossiste (section 4bis). `lignes` est un JSON texte
    (comme ImportLog.erreurs_detail) plutôt qu'une table enfant relationnelle.
    """
    __tablename__ = "commandes_validees"

    officine_id = Column(Uuid(as_uuid=True), ForeignKey("officines.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    format = Column(String, nullable=False)  # "pdf" / "xlsx"
    lignes = Column(Text, nullable=False)     # JSON : [{code, designation, qte_recommandee, qte_validee}]
