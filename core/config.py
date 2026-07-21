import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "fallback_secret_key_por_defecto")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    RESET_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("RESET_TOKEN_EXPIRE_MINUTES", "10"))

    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@tudominio.com")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "API Seguridad")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    MAX_FAILED_ATTEMPTS: int = 5
    LOCK_DURATION_MINUTES: int = 15

    def __init__(self) -> None:
        if not self.DATABASE_URL:
            raise ValueError("CRÍTICO: La variable DATABASE_URL no está configurada en el .env")


settings = Settings()
