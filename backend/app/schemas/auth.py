from pydantic import BaseModel, EmailStr
from typing import Optional

class OfficineCreate(BaseModel):
    nom: str

class SetupData(BaseModel):
    email: EmailStr
    password: str
    officine: OfficineCreate

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    officine_nom: str

class TokenData(BaseModel):
    user_id: Optional[str] = None
    officine_id: Optional[str] = None