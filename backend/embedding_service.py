# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         Text embedding service
# =======================================================================

from sentence_transformers import SentenceTransformer
from typing import List
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    _instance = None
    _model = None
    _executor = ThreadPoolExecutor(max_workers=2)  # Thread pool for CPU-intensive work

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            self._load_model()

    def _load_model(self):
        """Load the SentenceTransformer model with GPU support if available"""
        try:
            logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
            logger.info(f"Using compute device: {settings.DEVICE}")
            
            # Load model with device specification
            self._model = SentenceTransformer(settings.EMBEDDING_MODEL, device=settings.DEVICE)
            
            # Log GPU memory if available
            if settings.DEVICE == "cuda":
                import torch
                mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
                logger.info(f"CUDA GPU Memory: {mem:.1f} GB")
            elif settings.DEVICE == "mps":
                logger.info("MPS (Metal Performance Shaders) acceleration enabled")
            
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {str(e)}")
            raise RuntimeError(f"Could not load embedding model: {str(e)}")

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text string (synchronous)"""
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        try:
            embedding = self._model.encode(text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of text strings (synchronous)"""
        if not texts:
            return []
        
        try:
            embeddings = self._model.encode(texts, convert_to_tensor=False)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            raise

    async def embed_text_async(self, text: str) -> List[float]:
        """Generate embedding for a single text string (async - runs in thread pool)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.embed_text, text)

    async def embed_batch_async(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of text strings (async - runs in thread pool)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.embed_batch, texts)

# Global instance
embedding_service = EmbeddingService()

