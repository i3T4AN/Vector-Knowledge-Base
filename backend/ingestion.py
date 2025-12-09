# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         Document ingestion pipeline
# =======================================================================

"""
Ingestion Service - Handles file upload and processing
"""
from fastapi import UploadFile
import os
import re
import uuid
import time
import logging
from typing import Dict, Any
from config import settings
from extractors.factory import ExtractorFactory
from chunker import chunker
from embedding_service import embedding_service
from vector_db import vector_db
from exceptions import InvalidFileFormatError, FileSizeExceededError, ExtractionError

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to be safe for all filesystems.
    
    - Removes path components (prevents path traversal)
    - Removes null bytes and control characters
    - Replaces Windows-illegal characters: < > : " / \\ | ? *
    - Limits filename length to 200 characters
    - Handles empty or whitespace-only names
    """
    # Remove path components
    filename = os.path.basename(filename)
    
    # Remove null bytes and control characters
    filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
    
    # Replace Windows-illegal characters: < > : " / \ | ? *
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Limit length (255 is common max, leave room for unique suffix)
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200-len(ext)] + ext
    
    # Handle empty or whitespace-only names
    if not filename.strip():
        filename = "unnamed_file"
    
    return filename.strip()


class IngestionService:
    def __init__(self):
        pass
    
    async def process_file(self, file: UploadFile, extra_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process an uploaded file through the ingestion pipeline.
        """
        try:
            # Save file temporarily (use basename to avoid path issues)
            file_id = str(uuid.uuid4())
            safe_filename = sanitize_filename(file.filename)
            file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)
            
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            logger.info(f"Saved file: {safe_filename}")
            
            # Extract text
            extractor = ExtractorFactory.get_extractor(file_path)
            text, extracted_metadata = extractor.extract(file_path)
            
            if not text or not text.strip():
                raise ExtractionError(f"No text could be extracted from {safe_filename}")
            
            # Chunk text
            chunks = chunker.chunk_text(text)
            logger.info(f"Created {len(chunks)} chunks from {safe_filename}")
            
            # Prepare metadata
            metadata = extra_metadata or {}
            metadata["filename"] = safe_filename  # Use safe_filename instead of file.filename
            metadata["file_id"] = file_id
            metadata["upload_date"] = time.time()
            metadata["total_chunks"] = len(chunks)
            
            # Embed and store chunks
            document_id = str(uuid.uuid4())
            
            # Extract all chunk texts first
            chunk_texts = []
            for chunk_data in chunks:
                chunk_text = chunk_data.get("text", chunk_data) if isinstance(chunk_data, dict) else chunk_data
                chunk_texts.append(chunk_text)
            
            # OPTIMIZATION: Batch embed all chunks at once (async, runs in thread pool)
            vectors = await embedding_service.embed_batch_async(chunk_texts)
            
            # Prepare metadata for all chunks
            metadata_list = []
            for i, chunk_text in enumerate(chunk_texts):
                chunk_metadata = {
                    **metadata,
                    "text": chunk_text,
                    "chunk_index": i,
                    "document_id": document_id
                }
                metadata_list.append(chunk_metadata)
            
            # Batch insert all vectors
            await vector_db.upsert_vectors(vectors, metadata_list)
            
            return {
                "file_id": file_id,
                "filename": safe_filename,  # Use safe_filename here too
                "status": "success",
                "chunks_count": len(chunks),
                "document_id": document_id,
                "message": f"Successfully processed {safe_filename}"
            }
            
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {e}")
            raise

    async def process_file_batch(self, file: UploadFile, extra_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a file for batch ingestion (save, extract, chunk) but DO NOT embed or upsert.
        Returns the chunks and metadata for batch processing by the caller.
        """
        try:
            # Save file temporarily
            file_id = str(uuid.uuid4())
            safe_filename = sanitize_filename(file.filename)
            file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)
            
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            logger.info(f"Saved file for batch: {safe_filename}")
            
            # Extract text
            extractor = ExtractorFactory.get_extractor(file_path)
            text, extracted_metadata = extractor.extract(file_path)
            
            if not text or not text.strip():
                raise ExtractionError(f"No text could be extracted from {safe_filename}")
            
            # Chunk text
            chunks = chunker.chunk_text(text)
            
            # Prepare metadata
            metadata = extra_metadata or {}
            metadata["filename"] = safe_filename
            metadata["file_id"] = file_id
            metadata["upload_date"] = time.time()
            metadata["total_chunks"] = len(chunks)
            
            # Prepare chunks with metadata
            chunks_with_metadata = []
            for i, chunk_data in enumerate(chunks):
                chunk_text = chunk_data.get("text", chunk_data) if isinstance(chunk_data, dict) else chunk_data
                
                chunk_metadata = {
                    **metadata,
                    "text": chunk_text,
                    "chunk_index": i
                    # document_id will be assigned by caller
                }
                chunks_with_metadata.append({
                    "text": chunk_text,
                    "metadata": chunk_metadata
                })
            
            return {
                "filename": safe_filename,
                "file_id": file_id,
                "chunks": chunks_with_metadata,
                "chunks_count": len(chunks)
            }
            
        except Exception as e:
            logger.error(f"Error processing file batch {file.filename}: {e}")
            raise

# Global instance
ingestion_service = IngestionService()
