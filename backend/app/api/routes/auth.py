from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_password_hash, create_access_token, verify_password
from app.schemas.auth import SetupData, UserLogin, PasswordChange, Token
from app.models.officine import Officine
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.get("/is-setup")
def is_setup(db: Session = Depends(get_db)):
    """Indique si l'application a déjà été configurée (premier lancement)."""
    configured = db.query(User).first() is not None
    return {"configured": configured}


@router.post("/setup", response_model=Token)
def setup(data: SetupData, db: Session = Depends(get_db)):
    """
    Configuration initiale — crée l'officine et le compte unique.
    Ne fonctionne que si aucun compte n'existe encore.
    """
    if db.query(User).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="L'application est déjà configurée. Utilisez la page de connexion."
        )

    officine = Officine(nom=data.officine.nom)
    db.add(officine)
    db.commit()
    db.refresh(officine)

    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        officine_id=officine.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(data={"sub": str(user.id), "officine_id": str(officine.id)})
    return {"access_token": access_token, "token_type": "bearer", "officine_nom": officine.nom}


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants incorrects")

    officine = db.query(Officine).filter(Officine.id == user.officine_id).first()
    access_token = create_access_token(data={"sub": str(user.id), "officine_id": str(user.officine_id)})
    return {"access_token": access_token, "token_type": "bearer", "officine_nom": officine.nom}


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    return {"message": "Déconnexion réussie. Supprimez le token côté client."}


@router.patch("/me/password")
def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Permet au pharmacien de changer son mot de passe."""
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mot de passe actuel incorrect")

    current_user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    return {"message": "Mot de passe mis à jour avec succès."}
