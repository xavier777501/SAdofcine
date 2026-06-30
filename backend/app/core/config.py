from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "SAD OFFICINE"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Sécurité
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24h

    # Base de données
    DATABASE_URL: str

    # CORS (Frontend)
    FRONTEND_URL: str = "http://localhost:5173"

    # Uploads
    MAX_UPLOAD_SIZE_MB: int = 10
    UPLOAD_DIR: str = "./uploads"

    # Paramètres métier par défaut
    DEFAULT_ORDER_COST: float = 2500
    DEFAULT_HOLDING_RATE: float = 0.20
    DEFAULT_CYCLE_DAYS: int = 10

    # Facteurs Z (Niveaux de service VED)
    Z_VITAL: float = 2.326
    Z_ESSENTIEL: float = 1.645
    Z_DESIRABLE: float = 1.282
    Z_NON_RENSEIGNE: float = 1.645

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()