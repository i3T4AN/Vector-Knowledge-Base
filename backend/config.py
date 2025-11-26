# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         Backend configuration settings
# =======================================================================

import os
from typing import List, Set
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # Qdrant Configuration
    QDRANT_HOST: str = Field(default="localhost", description="Qdrant server host")
    QDRANT_PORT: int = Field(default=6333, description="Qdrant server port")
    QDRANT_COLLECTION: str = Field(default="vector_db", description="Name of the Qdrant collection")

    # Upload Configuration
    UPLOAD_DIR: str = Field(default="uploads", description="Directory to store uploaded files")
    MAX_FILE_SIZE: int = Field(default=10 * 1024 * 1024, description="Maximum file size in bytes (default 10MB)")
    ALLOWED_EXTENSIONS: Set[str] = Field(default={".pdf", ".txt", ".md", ".docx", ".py", ".js", ".html", ".css"}, description="Allowed file extensions")

    # Embedding Model Configuration
    EMBEDDING_MODEL: str = Field(default="all-mpnet-base-v2", description="SentenceTransformer model name")
    CHUNK_SIZE: int = Field(default=500, description="Text chunk size for embeddings")
    CHUNK_OVERLAP: int = Field(default=50, description="Overlap between text chunks")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

# Create global settings instance
settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
