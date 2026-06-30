from pydantic import BaseModel, EmailStr
from typing import Optional

class OfficineCreate(BaseModel):
    nom: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    officine: OfficineCreate

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[str] = None
    officine_id: Optional[str] = None