from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    get_password_hash,
    create_access_token,
    verify_password,
    generate_reset_code,
    hash_reset_token,
)
from app.schemas.auth import SetupData, UserLogin, PasswordChange, Token, ForgotPasswordRequest, ResetPasswordRequest
from app.models.officine import Officine
from app.models.user import User
from app.models.password_reset_token import PasswordResetToken
from app.services.email import send_password_reset_email
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentification"])

MAX_TENTATIVES_CODE = 5


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


@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Envoie un code de vérification par email si le compte existe.
    Renvoie toujours le même message, que l'email existe ou non, pour ne pas
    révéler quels emails sont enregistrés.
    """
    user = db.query(User).filter(User.email == data.email).first()
    if user:
        # Invalide les codes précédents encore actifs, pour n'avoir qu'un seul code valide à la fois.
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        ).update({"used_at": datetime.utcnow()})

        raw_code, code_hash = generate_reset_code()
        expires_at = datetime.utcnow() + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
        db.add(PasswordResetToken(user_id=user.id, token_hash=code_hash, expires_at=expires_at))
        db.commit()

        send_password_reset_email(user.email, raw_code)

    return {"message": "Si un compte existe avec cet email, un code de vérification vient d'être envoyé."}


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Réinitialise le mot de passe à partir du code de vérification reçu par email."""
    erreur_code = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Code invalide ou expiré. Refaites une demande.",
    )

    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise erreur_code

    reset_token = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )
    if not reset_token or reset_token.expires_at < datetime.utcnow():
        raise erreur_code

    if reset_token.attempts >= MAX_TENTATIVES_CODE:
        reset_token.used_at = datetime.utcnow()
        db.commit()
        raise erreur_code

    if hash_reset_token(data.code) != reset_token.token_hash:
        reset_token.attempts += 1
        db.commit()
        raise erreur_code

    user.hashed_password = get_password_hash(data.new_password)
    reset_token.used_at = datetime.utcnow()
    db.commit()

    return {"message": "Mot de passe réinitialisé avec succès."}
