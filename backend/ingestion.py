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

class IngestionService:
    def __init__(self):
        pass
    
    async def process_file(self, file: UploadFile, extra_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process an uploaded file through the ingestion pipeline.
        """
        try:
            # Save file temporarily
            file_id = str(uuid.uuid4())
            file_path = os.path.join(settings.UPLOAD_DIR, file.filename)
            
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            logger.info(f"Saved file: {file.filename}")
            
            # Extract text
            extractor = ExtractorFactory.get_extractor(file_path)
            text, extracted_metadata = extractor.extract(file_path)
            
            if not text or not text.strip():
                raise ExtractionError(f"No text could be extracted from {file.filename}")
            
            # Chunk text
            chunks = chunker.chunk_text(text)
            logger.info(f"Created {len(chunks)} chunks from {file.filename}")
            
            # Prepare metadata
            metadata = extra_metadata or {}
            metadata["filename"] = file.filename
            metadata["file_id"] = file_id
            metadata["upload_date"] = time.time()
            metadata["total_chunks"] = len(chunks)
            
            # Embed and store chunks
            document_id = str(uuid.uuid4())
            vectors = []
            metadata_list = []
            
            for i, chunk_data in enumerate(chunks):
                # Extract text from chunk data (chunker returns list of dicts)
                chunk_text = chunk_data.get("text", chunk_data) if isinstance(chunk_data, dict) else chunk_data
                
                embedding = embedding_service.embed_text(chunk_text)
                chunk_metadata = {
                    **metadata,
                    "text": chunk_text,
                    "chunk_index": i,
                    "document_id": document_id
                }
                
                vectors.append(embedding)
                metadata_list.append(chunk_metadata)
            
            # Batch insert all vectors
            vector_db.upsert_vectors(vectors, metadata_list)
            
            return {
                "file_id": file_id,
                "filename": file.filename,
                "status": "success",
                "chunks_count": len(chunks),
                "document_id": document_id,
                "message": f"Successfully processed {file.filename}"
            }
            
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {e}")
            raise

# Global instance
ingestion_service = IngestionService()
