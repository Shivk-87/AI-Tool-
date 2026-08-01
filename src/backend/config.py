"""Configuration management for Codebase Steward backend."""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://steward:steward@localhost:5432/codebase_steward"
    )
    
    # Milvus Vector DB
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", 19530))
    MILVUS_DB_NAME: str = os.getenv("MILVUS_DB_NAME", "codebase_steward")
    MILVUS_COLLECTION_NAME: str = os.getenv("MILVUS_COLLECTION_NAME", "code_snippets")
    
    # Model Server
    MODEL_SERVER_URL: str = os.getenv("MODEL_SERVER_URL", "http://localhost:8001")
    MODEL_EMBEDDING_ENDPOINT: str = "/embeddings"
    MODEL_SUGGEST_ENDPOINT: str = "/generate"
    
    # Redis Cache
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", 3600))  # 1 hour
    
    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    
    # Indexing
    MAX_CHUNK_SIZE: int = int(os.getenv("MAX_CHUNK_SIZE", 1024))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", 200))
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", 1024))
    VECTOR_SEARCH_LIMIT: int = int(os.getenv("VECTOR_SEARCH_LIMIT", 100))
    
    # API
    API_TITLE: str = "Codebase Steward API"
    API_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    class Config:
        env_file = ".env.local"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
