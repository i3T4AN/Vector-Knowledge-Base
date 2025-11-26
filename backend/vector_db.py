# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         Qdrant vector database operations
# =======================================================================

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams
from typing import List, Dict, Any, Optional
import logging
import uuid
from config import settings

logger = logging.getLogger(__name__)

class VectorDBClient:
    def __init__(self):
        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT
        )
        self.collection_name = settings.QDRANT_COLLECTION

    def ensure_collection(self):
        """Ensure the collection exists with the correct configuration"""
        try:
            collections = self.client.get_collections()
            exists = any(c.name == self.collection_name for c in collections.collections)
            
            if not exists:
                logger.info(f"Creating collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
                )
                logger.info("Collection created successfully")
            else:
                logger.info(f"Collection {self.collection_name} already exists")
        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")
            raise

    def upsert_vectors(self, vectors: List[List[float]], metadata_list: List[Dict[str, Any]]):
        """Insert or update vectors with metadata"""
        if len(vectors) != len(metadata_list):
            raise ValueError("Vectors and metadata list must have the same length")
        
        points = []
        for i, (vector, metadata) in enumerate(zip(vectors, metadata_list)):
            # Generate a deterministic ID if not provided, or use a random one
            # For chunks, we might want a deterministic ID based on doc_id + chunk_index
            # But for now, let's generate a UUID if not present
            point_id = str(uuid.uuid4())
            
            points.append(models.PointStruct(
                id=point_id,
                vector=vector,
                payload=metadata
            ))
            
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"Upserted {len(points)} vectors")
        except Exception as e:
            logger.error(f"Failed to upsert vectors: {e}")
            raise

    def search(self, query_vector: List[float], limit: int = 5, filter_criteria: Optional[Dict] = None) -> List[Dict]:
        """Search for similar vectors"""
        try:
            # Convert dictionary filter to Qdrant Filter object if needed
            query_filter = filter_criteria
            if filter_criteria and isinstance(filter_criteria, dict):
                must_conditions = []
                for key, value in filter_criteria.items():
                    if key == "date_range" and isinstance(value, dict):
                        # Handle range filter for upload_date
                        # Expects value to be {'gte': timestamp, 'lte': timestamp}
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
                        # Handle 'one of' filter (e.g. multiple extensions)
                        must_conditions.append(
                            models.FieldCondition(
                                key=key,
                                match=models.MatchAny(any=value)
                            )
                        )
                    else:
                        # Exact match
                        must_conditions.append(
                            models.FieldCondition(
                                key=key,
                                match=models.MatchValue(value=value)
                            )
                        )
                query_filter = models.Filter(must=must_conditions)

            search_result = self.client.search(
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

    def list_documents(self) -> List[Dict]:
        """List all unique documents (grouped by filename/document_id)"""
        # This is a simplified version. For large datasets, we'd need pagination/scrolling.
        # We'll use scroll to get a sample or try to group if possible.
        # Qdrant doesn't have a direct "list unique values" API efficiently without grouping.
        # For now, let's just scroll and collect unique filenames manually for small scale.
        # OR better: use the 'group' search API if available, but that requires a vector query usually.
        # Let's just scroll through all points (limit 1000) and deduplicate in python for now.
        
        try:
            # Scroll through points
            points, _ = self.client.scroll(
                collection_name=self.collection_name,
                limit=100,
                with_payload=True,
                with_vectors=False
            )
            
            unique_docs = {}
            for point in points:
                if point.payload:
                    doc_name = point.payload.get("filename") or point.payload.get("course_name")
                    if doc_name and doc_name not in unique_docs:
                        unique_docs[doc_name] = {
                            "filename": doc_name,
                            "id": point.payload.get("file_id"),
                            "upload_date": point.payload.get("upload_date"),
                            "total_chunks": point.payload.get("total_chunks"),
                            "metadata": point.payload
                        }
            
            return list(unique_docs.values())
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            raise

    def delete_document(self, key: str, value: Any):
        """Delete documents by metadata field (e.g., filename)"""
        try:
            self.client.delete(
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
            logger.info(f"Deleted documents where {key}={value}")
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            raise

# Global instance
vector_db = VectorDBClient()
