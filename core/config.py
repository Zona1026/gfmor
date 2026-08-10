from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """
    應用程式的設定，會從 .env 檔案中讀取環境變數。
    """
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    FRONTEND_URL: str = "http://127.0.0.1:5173"
    ADMIN_PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None
    SMTP_FROM_NAME: Optional[str] = None
    SMTP_USE_TLS: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"

# 建立一個全域可用的設定實例
settings = Settings()
