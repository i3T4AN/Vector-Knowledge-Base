# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         Qdrant vector database operations (Async)
# =======================================================================

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams
from typing import List, Dict, Any, Optional
import logging
import uuid
from config import settings
from document_registry import document_registry

logger = logging.getLogger(__name__)

class VectorDBClient:
    """
    Async Qdrant client wrapper for vector database operations.
    All methods are async to avoid blocking the FastAPI event loop.
    """
    
    def __init__(self):
        self.client = AsyncQdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT
        )
        self.collection_name = settings.QDRANT_COLLECTION

    async def ensure_collection(self):
        """Ensure the collection exists with the correct configuration"""
        try:
            collections = await self.client.get_collections()
            exists = any(c.name == self.collection_name for c in collections.collections)
            
            if not exists:
                logger.info(f"Creating collection: {self.collection_name}")
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
                )
                logger.info("Collection created successfully")
            else:
                logger.info(f"Collection {self.collection_name} already exists")
        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")
            raise

    async def reset_collection(self):
        """Delete and recreate the collection"""
        try:
            logger.info(f"Resetting collection: {self.collection_name}")
            await self.client.delete_collection(self.collection_name)
            await self.ensure_collection()
            document_registry.clear()  # Clear document registry
            logger.info("Collection reset successfully")
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            raise

    async def upsert_vectors(self, vectors: List[List[float]], metadata_list: List[Dict[str, Any]]):
        """Insert or update vectors with metadata"""
        if len(vectors) != len(metadata_list):
            raise ValueError("Vectors and metadata list must have the same length")
        
        points = []
        for i, (vector, metadata) in enumerate(zip(vectors, metadata_list)):
            point_id = str(uuid.uuid4())
            
            points.append(models.PointStruct(
                id=point_id,
                vector=vector,
                payload=metadata
            ))
            
        try:
            await self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"Upserted {len(points)} vectors")
        except Exception as e:
            logger.error(f"Failed to upsert vectors: {e}")
            raise

    async def upsert_batch(self, points: List[Dict]) -> None:
        """
        Upsert multiple points, splitting into smaller chunks to avoid timeouts.
        Points format: [{"id": ..., "vector": ..., "payload": {...}}, ...]
        """
        if not points:
            return
        
        logger.info(f"Batch upserting {len(points)} vectors")
        
        try:
            from qdrant_client.models import PointStruct
            
            # Split into chunks of 500 to avoid timeout on large batches
            CHUNK_SIZE = 500
            total_points = len(points)
            
            for i in range(0, total_points, CHUNK_SIZE):
                chunk = points[i:i + CHUNK_SIZE]
                chunk_num = (i // CHUNK_SIZE) + 1
                total_chunks = (total_points + CHUNK_SIZE - 1) // CHUNK_SIZE
                
                logger.info(f"Upserting chunk {chunk_num}/{total_chunks} ({len(chunk)} vectors)")
                
                qdrant_points = [
                    PointStruct(
                        id=point['id'],
                        vector=point['vector'],
                        payload=point['payload']
                    )
                    for point in chunk
                ]
                
                await self.client.upsert(
                    collection_name=self.collection_name,
                    points=qdrant_points,
                    wait=True
                )
            
            logger.info(f"Successfully upserted {total_points} vectors in {total_chunks} chunks")
        except Exception as e:
            logger.error(f"Batch upsert failed: {e}")
            raise

    async def search(self, query_vector: List[float], limit: int = 5, filter_criteria: Optional[Dict] = None) -> List[Dict]:
        """Search for similar vectors"""
        try:
            # Convert dictionary filter to Qdrant Filter object if needed
            query_filter = filter_criteria
            if filter_criteria and isinstance(filter_criteria, dict):
                must_conditions = []
                for key, value in filter_criteria.items():
                    if key == "date_range" and isinstance(value, dict):
                        must_conditions.append(
                            models.FieldCondition(
                                key="upload_date",
                                range=models.Range(
                                    gte=value.get("gte"),
                                    lte=value.get("lte")
                                )
                            )
                        )
                    elif isinstance(value, list):
                        must_conditions.append(
                            models.FieldCondition(
                                key=key,
                                match=models.MatchAny(any=value)
                            )
                        )
                    else:
                        must_conditions.append(
                            models.FieldCondition(
                                key=key,
                                match=models.MatchValue(value=value)
                            )
                        )
                query_filter = models.Filter(must=must_conditions)

            search_result = await self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=query_filter
            )
            
            results = []
            for hit in search_result:
                results.append({
                    "id": hit.id,
                    "score": hit.score,
                    "metadata": hit.payload,
                    "text": hit.payload.get("text", "") if hit.payload else ""
                })
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    async def list_documents(self) -> List[Dict]:
        """List all unique documents using registry for O(1) lookup"""
        try:
            # Use registry for O(1) document listing
            docs = document_registry.list_all()
            
            # If registry is empty but collection might have data, sync first
            if not docs:
                collection_info = await self.client.get_collection(self.collection_name)
                if collection_info.points_count > 0:
                    logger.info("Registry empty but collection has data, syncing...")
                    await document_registry.sync_from_qdrant(self)
                    docs = document_registry.list_all()
            
            return docs
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            raise

    async def delete_document(self, key: str, value: Any):
        """Delete documents by metadata field (e.g., filename)"""
        try:
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key=key,
                                match=models.MatchValue(value=value)
                            )
                        ]
                    )
                )
            )
            
            # Also unregister from document registry
            if key == "filename":
                document_registry.unregister_by_filename(value)
            
            logger.info(f"Deleted documents where {key}={value}")
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            raise

    async def get_all_embeddings(self) -> List[Dict[str, Any]]:
        """
        Fetch all embeddings and their metadata from the collection.
        Returns a list of dicts with 'id', 'vector', and 'metadata'.
        """
        try:
            all_points = []
            offset = None
            limit = 100
            
            while True:
                points, next_offset = await self.client.scroll(
                    collection_name=self.collection_name,
                    limit=limit,
                    offset=offset,
                    with_payload=True,
                    with_vectors=True
                )
                
                for point in points:
                    all_points.append({
                        "id": point.id,
                        "vector": point.vector,
                        "metadata": point.payload
                    })
                
                offset = next_offset
                if offset is None:
                    break
                    
            return all_points
        except Exception as e:
            logger.error(f"Failed to fetch all embeddings: {e}")
            return []

    async def get_vectors_by_ids(self, ids: List[str]) -> List[Dict[str, Any]]:
        """Fetch vectors for specific IDs"""
        try:
            points = await self.client.retrieve(
                collection_name=self.collection_name,
                ids=ids,
                with_vectors=True,
                with_payload=True
            )
            
            results = []
            for point in points:
                results.append({
                    "id": point.id,
                    "vector": point.vector,
                    "metadata": point.payload
                })
            return results
        except Exception as e:
            logger.error(f"Failed to fetch vectors by IDs: {e}")
            return []

    async def set_payload(self, points: List[str], payload: Dict[str, Any]):
        """Set payload for specific points (used for clustering)"""
        try:
            await self.client.set_payload(
                collection_name=self.collection_name,
                points=points,
                payload=payload
            )
        except Exception as e:
            logger.error(f"Failed to set payload: {e}")
            raise

# Global instance
vector_db = VectorDBClient()
