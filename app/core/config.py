from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # API Configuration
    API_V1_PREFIX: str = "/api"
    PROJECT_NAME: str = "Multi-College CMS"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    BASE_URL: str = "https://portal.ipsa.ac.in"
    
    # Database
    DATABASE_URL: str
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:4200"]
    CORS_ORIGIN_REGEX: str = r"https://([a-z0-9-]+\.)*ipsa\.ac\.in"
    
    # File Upload
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 5242880  # 5MB
    
    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    
    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_BUCKET: str = "journals"
    
    # Meritto CRM
    MERITTO_SECRET_KEY: str = ""
    MERITTO_ACCESS_KEY: str = ""

    # Ambition Mic contest email delivery (Brevo Transactional Email)
    BREVO_API_KEY: str = ""
    BREVO_API_BASE_URL: str = "https://api.brevo.com/v3"
    BREVO_FROM_NAME: str = "Ambition Mic Contest"
    BREVO_FROM_EMAIL: str = ""
    AMBITION_MIC_RECIPIENT: str = ""
    AMBITION_MIC_MAX_VIDEO_SIZE: int = 20 * 1024 * 1024
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env


settings = Settings()
