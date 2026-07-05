import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.officine import Officine

# HTTPBearer → Swagger affiche un simple champ "Value" où coller le token
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Extrait l'utilisateur courant depuis le token JWT.
    Utilisé pour les routes qui ont besoin de l'objet User complet.
    """
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte désactivé")
    return user


def get_current_officine(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Officine:
    """
    Récupère l'officine de l'utilisateur courant.
    
    C'est LA dépendance critique pour l'isolation multi-locataire (US-A3).
    Toute route métier qui manipule des données (imports, références, paramètres)
    DOIT utiliser cette dépendance pour filtrer automatiquement par officine_id.
    
    Usage dans une route :
        @router.get("/imports")
        def list_imports(officine: Officine = Depends(get_current_officine)):
            return db.query(Import).filter(Import.officine_id == officine.id).all()
    """
    officine = db.query(Officine).filter(Officine.id == current_user.officine_id).first()
    if officine is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Officine introuvable pour cet utilisateur"
        )
    return officine