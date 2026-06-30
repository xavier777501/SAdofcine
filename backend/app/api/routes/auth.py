from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_password_hash, create_access_token, verify_password
from app.schemas.auth import UserCreate, UserLogin, Token
from app.models.officine import Officine
from app.models.user import User
from app.api.deps import get_current_user  # ← AJOUTÉ

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/register", response_model=Token)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # 1. Vérifier si l'email existe
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email déjà enregistré")

    # 2. Créer l'officine
    officine = Officine(nom=user_data.officine.nom)
    db.add(officine)
    db.commit()
    db.refresh(officine)

    # 3. Créer l'utilisateur lié à l'officine
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        officine_id=officine.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 4. Générer le token JWT
    access_token = create_access_token(data={"sub": str(user.id), "officine_id": str(officine.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Identifiants incorrects")

    if not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Identifiants incorrects")

    access_token = create_access_token(data={"sub": str(user.id), "officine_id": str(user.officine_id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """
    Endpoint symbolique de déconnexion.
    Avec JWT stateless, l'invalidation côté serveur n'est pas nécessaire.
    Le frontend doit supprimer le token du localStorage/cookie.
    """
    return {"message": "Déconnexion réussie. Supprimez le token côté client."}