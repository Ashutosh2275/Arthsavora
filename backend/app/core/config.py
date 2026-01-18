from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "ARTHSAVORA"
    MONGODB_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # Cloud Storage (Phase 9)
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # AI Chatbot (Phase 13)
    GEMINI_API_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()