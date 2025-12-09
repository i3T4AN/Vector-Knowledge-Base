# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         Backend configuration settings
# =======================================================================

import os
from typing import List, Set
from pydantic_settings import BaseSettings
from pydantic import Field
import logging

logger = logging.getLogger(__name__)

def detect_device() -> str:
    """
    Auto-detect the best available compute device.
    Priority: MPS (Apple Silicon) > CUDA (NVIDIA) > CPU
    """
    try:
        import torch
        
        # Check for Apple Silicon MPS
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            logger.info("GPU detected: Apple MPS (Metal Performance Shaders)")
            return "mps"
        
        # Check for NVIDIA CUDA
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            logger.info(f"GPU detected: CUDA ({device_name})")
            return "cuda"
        
        logger.info("No GPU detected, using CPU")
        return "cpu"
        
    except ImportError:
        logger.warning("PyTorch not installed, defaulting to CPU")
        return "cpu"
    except Exception as e:
        logger.warning(f"Device detection failed: {e}, defaulting to CPU")
        return "cpu"


class Settings(BaseSettings):
    # Qdrant Configuration
    QDRANT_HOST: str = Field(default="localhost", description="Qdrant server host")
    QDRANT_PORT: int = Field(default=6333, description="Qdrant server port")
    QDRANT_COLLECTION: str = Field(default="vector_db", description="Name of the Qdrant collection")

    # Upload Configuration
    UPLOAD_DIR: str = Field(default="uploads", description="Directory to store uploaded files")
    MAX_FILE_SIZE: int = Field(default=50 * 1024 * 1024, description="Maximum file size in bytes (default 50MB)")
    ALLOWED_EXTENSIONS: Set[str] = Field(default={
        ".pdf", ".docx", ".pptx", ".ppt", ".xlsx", ".csv",
        ".jpg", ".jpeg", ".png", ".webp",
        ".txt", ".md",
        ".py", ".js", ".java", ".cpp", ".html", ".css", ".json", ".xml", ".yaml", ".yml", ".cs"
    }, description="Allowed file extensions")

    # Embedding Model Configuration
    EMBEDDING_MODEL: str = Field(default="all-mpnet-base-v2", description="SentenceTransformer model name")
    CHUNK_SIZE: int = Field(default=500, description="Text chunk size for embeddings")
    CHUNK_OVERLAP: int = Field(default=50, description="Overlap between text chunks")
    
    # Compute Device Configuration
    DEVICE: str = Field(default="auto", description="Compute device: 'auto', 'cpu', 'cuda', or 'mps'")
    
    # CORS Configuration (comma-separated list of allowed origins)
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:8001", "http://127.0.0.1:8001"],
        description="Allowed CORS origins. Use ['*'] to allow all (not recommended for production)"
    )
    
    # Admin Key for destructive operations
    ADMIN_KEY: str = Field(
        default="",
        description="Admin key for destructive operations (reset). Leave empty to disable protection."
    )
    
    # Rate Limiting (absurdly high defaults for personal use - won't affect normal usage)
    RATE_LIMIT_UPLOAD: str = Field(
        default="1000/minute",
        description="Rate limit for upload endpoints (e.g., '10/minute', '100/hour')"
    )
    RATE_LIMIT_SEARCH: str = Field(
        default="1000/minute",
        description="Rate limit for search endpoint"
    )
    RATE_LIMIT_RESET: str = Field(
        default="60/minute",
        description="Rate limit for reset endpoint (stricter for safety)"
    )

    class Config:
        env_file = "../.env"  # Look in project root, not backend/
        env_file_encoding = "utf-8"
        case_sensitive = True

# Create global settings instance
settings = Settings()

# Resolve device if set to auto
if settings.DEVICE == "auto":
    settings.DEVICE = detect_device()
else:
    logger.info(f"Using manually configured device: {settings.DEVICE}")

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

