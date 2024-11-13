# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # MongoDB Atlas Connection
    MONGODB_URL: str
    DB_NAME: str = "pdf_query_system"
    
    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str
    
    # OpenAI
    OPENAI_API_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()