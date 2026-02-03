"""
Application configuration using pydantic-settings.
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # App settings
    app_name: str = "Optira Document Transformer"
    debug: bool = False
    
    # Groq API
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_timeout: int = 60
    
    # File handling
    max_file_size_mb: int = 50
    temp_dir: str = "temp_uploads"
    
    # Supported file types
    supported_extensions: list[str] = [".docx", ".pdf", ".pptx"]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
