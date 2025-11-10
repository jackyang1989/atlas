import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "ATLAS"
    PROJECT_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./atlas.db")
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 7
    
    CERTS_DIR: str = os.getenv("CERTS_DIR", "/opt/atlas/certs")
    BACKUPS_DIR: str = os.getenv("BACKUPS_DIR", "/opt/atlas/backups")
    LOGS_DIR: str = os.getenv("LOGS_DIR", "/opt/atlas/logs")
    SING_BOX_CONFIG_PATH: str = os.getenv("SING_BOX_CONFIG_PATH", "/etc/sing-box/config.json")
    
    class Config:
        env_file = ".env"


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
