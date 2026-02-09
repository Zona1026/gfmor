from pydantic import BaseSettings

class Settings(BaseSettings):
    """
    應用程式的設定，會從 .env 檔案中讀取環境變數。
    """
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"

# 建立一個全域可用的設定實例
settings = Settings()
