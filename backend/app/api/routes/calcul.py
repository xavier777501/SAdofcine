from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_officine
from app.core.database import get_db
from app.models.officine import Officine
from app.services.calcul_officine import calculer_toutes_references

router = APIRouter(prefix="/calcul", tags=["Moteur de calcul"])


@router.post("/lancer")
def lancer_calcul(
    officine: Officine = Depends(get_current_officine),
    db: Session = Depends(get_db),
):
    """
    Relance le moteur SAD sur toutes les références de l'officine.
    Appelé automatiquement après chaque import ; peut aussi être déclenché manuellement.
    """
    resultat = calculer_toutes_references(officine.id, db)
    db.commit()
    return {"message": "Calcul terminé.", **resultat}
