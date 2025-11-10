"""
Configuration management for Terraform Assistant
"""
import os
from functools import lru_cache
from typing import Optional, List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Terraform Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    
    # Redis
    REDIS_URL: str = Field(..., env="REDIS_URL")
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = Field(None, env="OPENAI_API_KEY")
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    
    # Documentation URLs
    AWS_DOCS_BASE_URL: str = "https://registry.terraform.io/providers/hashicorp/aws/latest/docs"
    AZURE_DOCS_BASE_URL: str = "https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs"
    GCP_DOCS_BASE_URL: str = "https://registry.terraform.io/providers/hashicorp/google/latest/docs"
    
    # Cache settings
    CACHE_TTL: int = 3600  # 1 hour
    TEMPLATE_CACHE_TTL: int = 7200  # 2 hours
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Background tasks
    CELERY_BROKER_URL: Optional[str] = Field(None, env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: Optional[str] = Field(None, env="CELERY_RESULT_BACKEND")
    
    # Monitoring
    PROMETHEUS_ENABLED: bool = Field(default=False, env="PROMETHEUS_ENABLED")

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000"],
        env="CORS_ORIGINS"
    )
    ALLOWED_HOSTS: List[str] = Field(
        default=["*"],
        env="ALLOWED_HOSTS"
    )

    # Elasticsearch
    ELASTICSEARCH_URL: Optional[str] = Field(None, env="ELASTICSEARCH_URL")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "allow"
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()