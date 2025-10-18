# app/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # MongoDB Settings
    MONGODB_URL: str
    DB_NAME: str = "pdf_query_system"
    
    # Cloudinary Settings
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str
    
    # Gemini Settings
    GEMINI_API_KEY: str

    # OpenAI API Key (not required)
    OPENAI_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"

settings = Settings()