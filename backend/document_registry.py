# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         Document registry for O(1) document listing
# =======================================================================

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import time
import asyncio
from threading import Lock

logger = logging.getLogger(__name__)


class DocumentRegistry:
    """
    Maintains a registry of uploaded documents for O(1) listing.
    
    This avoids the O(n) complexity of scrolling through all vectors
    in Qdrant to deduplicate by document_id.
    """
    
    def __init__(self, registry_path: str = "data/documents.json"):
        self.registry_path = Path(registry_path)
        self._registry: Dict[str, dict] = {}
        self._lock = Lock()
        self._load()
    
    def _load(self) -> None:
        """Load registry from disk."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r') as f:
                    self._registry = json.load(f)
                logger.info(f"Loaded {len(self._registry)} documents from registry")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load registry, starting fresh: {e}")
                self._registry = {}
        else:
            logger.info("No existing registry found, starting fresh")
            self._registry = {}
    
    def _save(self) -> None:
        """Persist registry to disk."""
        try:
            # Ensure directory exists
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.registry_path, 'w') as f:
                json.dump(self._registry, f, indent=2, default=str)
        except IOError as e:
            logger.error(f"Failed to save registry: {e}")
            raise
    
    def register(self, document_id: str, metadata: dict) -> None:
        """
        Register a document in the registry.
        
        Args:
            document_id: Unique document identifier
            metadata: Document metadata (filename, upload_date, total_chunks, etc.)
        """
        with self._lock:
            # Don't re-register if already exists (idempotent)
            if document_id in self._registry:
                logger.debug(f"Document {document_id} already registered, updating")
            
            self._registry[document_id] = {
                "filename": metadata.get("filename"),
                "upload_date": metadata.get("upload_date", time.time()),
                "total_chunks": metadata.get("total_chunks", 1),
                "folder_path": metadata.get("folder_path"),
            }
            self._save()
            logger.debug(f"Registered document: {document_id}")
    
    def unregister(self, document_id: str) -> bool:
        """
        Remove a document from the registry.
        
        Args:
            document_id: Document ID to remove
            
        Returns:
            True if document was found and removed, False otherwise
        """
        with self._lock:
            if document_id in self._registry:
                del self._registry[document_id]
                self._save()
                logger.debug(f"Unregistered document: {document_id}")
                return True
            return False
    
    def unregister_by_filename(self, filename: str) -> int:
        """
        Remove all documents with a given filename.
        
        Args:
            filename: Filename to match
            
        Returns:
            Number of documents removed
        """
        with self._lock:
            to_remove = [
                doc_id for doc_id, meta in self._registry.items()
                if meta.get("filename") == filename
            ]
            for doc_id in to_remove:
                del self._registry[doc_id]
            
            if to_remove:
                self._save()
                logger.debug(f"Unregistered {len(to_remove)} documents with filename: {filename}")
            
            return len(to_remove)
    
    def list_all(self) -> List[dict]:
        """
        List all registered documents.
        
        Returns:
            List of document metadata dicts with 'id' field added
        """
        with self._lock:
            return [
                {
                    "id": doc_id,
                    "filename": meta.get("filename"),
                    "upload_date": meta.get("upload_date"),
                    "total_chunks": meta.get("total_chunks"),
                    "metadata": meta
                }
                for doc_id, meta in self._registry.items()
            ]
    
    def exists(self, document_id: str) -> bool:
        """Check if a document is registered."""
        with self._lock:
            return document_id in self._registry
    
    def get(self, document_id: str) -> Optional[dict]:
        """Get metadata for a specific document."""
        with self._lock:
            return self._registry.get(document_id)
    
    def count(self) -> int:
        """Get total number of registered documents."""
        with self._lock:
            return len(self._registry)
    
    def clear(self) -> None:
        """Clear the entire registry."""
        with self._lock:
            self._registry = {}
            self._save()
            logger.info("Registry cleared")
    
    async def sync_from_qdrant(self, vector_db_client) -> int:
        """
        Rebuild registry by scanning Qdrant collection.
        
        This is used for backwards compatibility when registry doesn't exist
        or needs to be rebuilt from existing data.
        
        Args:
            vector_db_client: VectorDBClient instance to scan
            
        Returns:
            Number of documents registered
        """
        logger.info("Syncing registry from Qdrant...")
        
        unique_docs = {}
        offset = None
        limit = 100
        
        while True:
            points, next_offset = await vector_db_client.client.scroll(
                collection_name=vector_db_client.collection_name,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            
            for point in points:
                if point.payload:
                    doc_id = point.payload.get("document_id") or point.payload.get("file_id")
                    
                    if doc_id and doc_id not in unique_docs:
                        unique_docs[doc_id] = {
                            "filename": point.payload.get("filename") or point.payload.get("course_name"),
                            "upload_date": point.payload.get("upload_date"),
                            "total_chunks": point.payload.get("total_chunks"),
                            "folder_path": point.payload.get("folder_path"),
                        }
            
            offset = next_offset
            if offset is None:
                break
        
        # Update registry
        with self._lock:
            self._registry = unique_docs
            self._save()
        
        logger.info(f"Synced {len(unique_docs)} documents from Qdrant to registry")
        return len(unique_docs)


# Global instance
document_registry = DocumentRegistry()
