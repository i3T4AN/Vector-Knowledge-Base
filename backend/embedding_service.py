# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         Text embedding service
# =======================================================================

from sentence_transformers import SentenceTransformer
from typing import List
import logging
from config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            self._load_model()

    def _load_model(self):
        """Load the SentenceTransformer model"""
        try:
            logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
            self._model = SentenceTransformer(settings.EMBEDDING_MODEL)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {str(e)}")
            raise RuntimeError(f"Could not load embedding model: {str(e)}")

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text string"""
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        try:
            embedding = self._model.encode(text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of text strings"""
        if not texts:
            return []
        
        # Filter out empty strings but keep track of indices if needed
        # For now, we assume valid input or let the model handle it
        
        try:
            embeddings = self._model.encode(texts, convert_to_tensor=False)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            raise

# Global instance
embedding_service = EmbeddingService()
