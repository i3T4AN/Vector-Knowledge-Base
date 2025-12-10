# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         FastAPI application and API endpoints
# =======================================================================

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, BackgroundTasks, Header
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import logging
import uvicorn
import os
import shutil
import numpy as np
import uuid
import time

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Import backend modules
from config import settings
from constants import FILTER_ALL, FOLDER_NULL, FOLDER_UNSORTED
from ingestion import ingestion_service
from embedding_service import embedding_service
from vector_db import vector_db
from document_registry import document_registry
from filesystem_db import fs_db
from exceptions import (
    VectorDBException,
    InvalidFileFormatError,
    FileSizeExceededError,
    ExtractionError,
    EmbeddingError,
    VectorDBError
)
from dimensionality_reduction import DimensionalityReducer
from clustering import ClusteringService
from jobs import create_job, update_job, get_job, list_jobs, JobStatus, JobType
from mcp_server import setup_mcp_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app initialization moved below lifespan definition

# Initialize Dimensionality Reducer
dim_reducer = DimensionalityReducer(method='pca', n_components=3)

# Initialize Clustering Service
clustering_service = ClusteringService(min_cluster_size=5)

# 3D visualization cache
_3d_cache = {
    "coords": None,      # np.ndarray of 3D coordinates
    "point_ids": None,   # List of point IDs
    "metadata": None,    # List of metadata dicts
    "is_valid": False
}

def invalidate_3d_cache():
    """Clear 3D cache when data changes"""
    global _3d_cache, dim_reducer
    _3d_cache = {"coords": None, "point_ids": None, "metadata": None, "is_valid": False}
    # Reset the dim_reducer so PCA refits on new data
    dim_reducer = DimensionalityReducer(method="pca", n_components=3)
    logger.info("3D cache invalidated")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events: startup and shutdown"""
    logger.info("Initializing Qdrant collection...")
    await vector_db.ensure_collection()
    logger.info("Qdrant ready - startup complete")
    
    # Initialize MCP server (if enabled)
    mcp = setup_mcp_server(app)
    if mcp:
        logger.info(f"MCP server ready at {settings.MCP_PATH}")
    
    yield
    logger.info("Shutting down...")

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Vector Database API",
    description="A vector database application for course material and projects",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure rate limiting (absurdly high defaults for personal use)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Exception Handlers
@app.exception_handler(InvalidFileFormatError)
async def invalid_format_handler(request: Request, exc: InvalidFileFormatError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "error_code": "INVALID_FORMAT"}
    )

@app.exception_handler(FileSizeExceededError)
async def file_size_handler(request: Request, exc: FileSizeExceededError):
    return JSONResponse(
        status_code=413,
        content={"detail": str(exc), "error_code": "FILE_TOO_LARGE"}
    )

@app.exception_handler(ExtractionError)
async def extraction_handler(request: Request, exc: ExtractionError):
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc), "error_code": "EXTRACTION_FAILED"}
    )

@app.exception_handler(VectorDBException)
async def vector_db_exception_handler(request: Request, exc: VectorDBException):
    # Catch-all for other custom exceptions (Embedding, DB)
    logger.error(f"Internal VectorDB error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "error_code": "INTERNAL_ERROR"}
    )

class UploadResponse(BaseModel):
    file_id: str
    filename: str
    status: str
    chunks_count: int
    document_id: str
    message: Optional[str] = None

class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    filters: Optional[Dict[str, Any]] = None
    cluster_filter: Optional[str] = None

class SearchResult(BaseModel):
    id: str
    score: float
    text: str
    metadata: Dict[str, Any]

class SearchResponse(BaseModel):
    results: List[SearchResult]
    count: int

@app.get("/health")
async def health_check():
    """Health check endpoint to verify the API is running"""
    logger.info("Health check endpoint called")
    return {
        "status": "healthy",
        "message": "Vector Database API is running",
        "version": "1.0.0"
    }

@app.get("/config/allowed-extensions")
async def get_allowed_extensions():
    """Return list of allowed file extensions for frontend validation."""
    return {"extensions": sorted(list(settings.ALLOWED_EXTENSIONS))}

@app.post("/search", response_model=SearchResponse)
@limiter.limit(settings.RATE_LIMIT_SEARCH)
async def search_documents(request: Request, search_req: SearchRequest):
    """
    Search for documents using vector similarity.
    """
    logger.info(f"Received search request: {search_req.query}")
    
    # 1. Generate embedding for the query
    try:
        query_vector = await embedding_service.embed_text_async(search_req.query)
    except Exception as e:
        raise EmbeddingError(f"Failed to embed query: {e}")
    
    # 2. Search in Vector DB
    try:
        # Handle cluster filtering
        search_filters = search_req.filters or {}
        if search_req.cluster_filter and search_req.cluster_filter != FILTER_ALL:
            try:
                search_filters["cluster"] = int(search_req.cluster_filter)
            except ValueError:
                pass # Ignore invalid cluster IDs

        results = await vector_db.search(
            query_vector=query_vector,
            limit=search_req.limit,
            filter_criteria=search_filters
        )
    except Exception as e:
        raise VectorDBError(f"Search operation failed: {e}")
    
    # 3. Format results
    formatted_results = []
    for hit in results:
        formatted_results.append(SearchResult(
            id=str(hit.get("id")),
            score=hit.get("score"),
            text=hit.get("text"),
            metadata=hit.get("metadata", {})
        ))
        
    return SearchResponse(
        results=formatted_results,
        count=len(formatted_results)
    )

class DocumentResponse(BaseModel):
    filename: str
    id: Optional[str] = None
    upload_date: Optional[float] = None
    total_chunks: Optional[int] = None
    metadata: Dict[str, Any]

@app.get("/documents", response_model=List[DocumentResponse])
async def list_documents():
    """
    List all uploaded documents.
    """
    logger.info("Listing all documents")
    try:
        documents = await vector_db.list_documents()
        return documents
    except Exception as e:
        logger.error(f"Failed to list documents: {str(e)}")
        raise VectorDBError(f"Failed to list documents: {str(e)}")

@app.delete("/documents/{filename}")
async def delete_document(filename: str):
    """
    Delete a document and all its chunks by filename.
    """
    logger.info(f"Deleting document: {filename}")
    try:
        # 1. Delete physical file if it exists
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Deleted physical file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete physical file {file_path}: {e}")
        else:
            logger.warning(f"Physical file not found: {file_path}")

        # 2. Delete vectors from Qdrant
        await vector_db.delete_document("filename", filename)
        
        # 3. Remove from file system organization
        await fs_db.remove_file_by_filename(filename)
        
        # Invalidate 3D cache
        invalidate_3d_cache()
        
        return {"status": "success", "message": f"Document {filename} deleted"}
    except Exception as e:
        logger.error(f"Failed to delete document: {str(e)}")
        raise VectorDBError(f"Failed to delete document: {str(e)}")

@app.post("/upload", response_model=UploadResponse)
@limiter.limit(settings.RATE_LIMIT_UPLOAD)
async def upload_file(
    request: Request,  # Required for rate limiting
    file: UploadFile = File(...),
    category: str = Form(...),
    tags: Optional[str] = Form(None),
    relative_path: Optional[str] = Form(None)
):
    """
    Upload a file to the vector database.
    Optionally specify relative_path to preserve folder structure.
    """
    logger.info(f"Received upload request for {file.filename}")
    
    # Validate file extension
    _, ext = os.path.splitext(file.filename)
    if ext.lower() not in settings.ALLOWED_EXTENSIONS:
        logger.warning(f"Rejected file {file.filename} with extension {ext}")
        raise InvalidFileFormatError(f"File type '{ext}' not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}")
    
    # Prepare metadata
    metadata = {
        "category": category
    }
    
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        metadata["tags"] = tag_list
        
    # Process file (IngestionService now raises exceptions)
    result = await ingestion_service.process_file(file, extra_metadata=metadata)
    
    # Handle folder structure if relative_path is provided
    target_folder_id = None
    if relative_path:
        logger.info(f"Processing folder path: {relative_path}")
        # Parse the path (e.g., "schoolwork/senior year/math")
        path_components = [p.strip() for p in relative_path.split('/') if p.strip()]
        
        if path_components:
            # Get or create the folder structure
            target_folder_id = await fs_db.get_or_create_folder_path(path_components)
            logger.info(f"Created/found folder structure, target folder ID: {target_folder_id}")
    
    # Move file to the target folder
    if target_folder_id:
        await fs_db.move_file_to_folder(result["document_id"], result["filename"], target_folder_id)
        logger.info(f"Moved {result['filename']} to folder {target_folder_id}")
    elif relative_path is not None:
        # relative_path was provided but empty, move to Root
        await fs_db.move_file_to_folder(result["document_id"], result["filename"], None)
    # else: file remains unsorted (default behavior)
    
    # Invalidate 3D cache since new data added
    invalidate_3d_cache()
    
    return UploadResponse(
        file_id=result.get("file_id", "unknown"),
        filename=result["filename"],
        status=result["status"],
        chunks_count=result.get("chunks_count", 0),
        document_id=result.get("document_id", ""),
        message=result.get("message")
    )

@app.post("/upload-batch")
@limiter.limit(settings.RATE_LIMIT_UPLOAD)
async def upload_folder_batch(
    request: Request,  # Required for rate limiting
    files: List[UploadFile] = File(...),
    category: str = Form(...),
    tags: Optional[str] = Form(None),
    relative_path: Optional[str] = Form(None)
):
    """
    Upload multiple files that share the same folder path.
    Optimized for batch processing with single folder query.
    """
    logger.info(f"Received batch upload: {len(files)} files, path: {relative_path}")
    
    # Validate all files
    valid_files = []
    rejected_files = []
    for file in files:
        _, ext = os.path.splitext(file.filename)
        if ext.lower() not in settings.ALLOWED_EXTENSIONS:
            rejected_files.append({
                "filename": file.filename,
                "reason": f"Invalid extension: {ext}"
            })
        else:
            valid_files.append(file)
    
    if not valid_files:
        if rejected_files:
             raise HTTPException(400, f"No valid files in batch. Rejected: {rejected_files}")
        raise HTTPException(400, "No files provided")
    
    # OPTIMIZATION 1: Resolve folder hierarchy ONCE
    target_folder_id = None
    if relative_path:
        path_components = [p.strip() for p in relative_path.split('/') if p.strip()]
        if path_components:
            target_folder_id = await fs_db.get_or_create_folder_path(path_components)
            logger.info(f"Batch folder resolved: {target_folder_id}")
    
    # Prepare metadata
    base_metadata = {"category": category}
    if tags:
        base_metadata["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
    
    # OPTIMIZATION 2: Process all files, collect all chunks
    all_chunks_data = []
    file_results = []
    
    # Process files in parallel/sequence (sequence for now to avoid complexity)
    for file in valid_files:
        try:
            # Use new batch processing method (does NOT embed/upsert)
            result = await ingestion_service.process_file_batch(file, extra_metadata=base_metadata)
            
            # Assign document_id to chunks
            document_id = str(uuid.uuid4())
            for chunk in result['chunks']:
                chunk['metadata']['document_id'] = document_id
            
            file_results.append({
                "filename": result['filename'],
                "chunks_count": result['chunks_count'],
                "document_id": document_id,
                "status": "success"
            })
            
            # Collect chunks for batch embedding
            all_chunks_data.extend(result['chunks'])
            
        except Exception as e:
            logger.error(f"Failed to process {file.filename}: {e}")
            rejected_files.append({
                "filename": file.filename,
                "reason": str(e)
            })
    
    if not all_chunks_data:
         return {
            "status": "partial_success",
            "uploaded": 0,
            "rejected": len(rejected_files),
            "files": [],
            "rejected_files": rejected_files
        }

    # OPTIMIZATION 3: Batch generate embeddings
    try:
        texts = [chunk['text'] for chunk in all_chunks_data]
        embeddings = await embedding_service.embed_batch_async(texts)
        
        # Prepare points for Qdrant
        points = []
        for i, chunk_data in enumerate(all_chunks_data):
            points.append({
                "id": str(uuid.uuid4()),
                "vector": embeddings[i],
                "payload": {
                    "text": chunk_data['text'],
                    **chunk_data['metadata']
                }
            })
            
        # OPTIMIZATION 4: Batch upsert to Qdrant
        await vector_db.upsert_batch(points)
        
        # Register documents in registry for O(1) listing
        for result in file_results:
            document_registry.register(result["document_id"], {
                "filename": result["filename"],
                "total_chunks": result["chunks_count"]
            })
        
    except Exception as e:
        logger.error(f"Batch embedding/upsert failed: {e}")
        raise HTTPException(500, f"Batch processing failed: {str(e)}")
    
    # OPTIMIZATION 5: Move all files to folder using same folder_id
    for result in file_results:
        if target_folder_id:
            await fs_db.move_file_to_folder(result["document_id"], result["filename"], target_folder_id)
        elif relative_path is not None:
             # relative_path provided but empty -> root
             await fs_db.move_file_to_folder(result["document_id"], result["filename"], None)
    
    # Return summary
    
    # Invalidate 3D cache
    invalidate_3d_cache()
    
    return {
        "status": "success",
        "uploaded": len(file_results),
        "rejected": len(rejected_files),
        "files": file_results,
        "rejected_files": rejected_files
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Vector Database API",
        "docs": "/docs",
        "health": "/health"
    }

# ==================== File System Endpoints ====================

class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[str] = None

class FolderUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[str] = None

class FileMoveRequest(BaseModel):
    document_id: str
    filename: str
    folder_id: Optional[str] = None

@app.get("/folders")
async def get_folders():
    """Get all folders."""
    try:
        folders = await fs_db.get_all_folders()
        return folders
    except Exception as e:
        logger.error(f"Failed to get folders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/folders")
async def create_folder(folder: FolderCreate):
    """Create a new folder."""
    try:
        folder_id = await fs_db.create_folder(folder.name, folder.parent_id)
        return {"id": folder_id, "name": folder.name, "parent_id": folder.parent_id}
    except Exception as e:
        logger.error(f"Failed to create folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/folders/{folder_id}")
async def update_folder(folder_id: str, folder: FolderUpdate):
    """Update a folder's name or move it to a new parent."""
    try:
        await fs_db.update_folder(folder_id, folder.name, folder.parent_id)
        return {"status": "success", "folder_id": folder_id}
    except Exception as e:
        logger.error(f"Failed to update folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/folders/{folder_id}")
async def delete_folder(folder_id: str):
    """Delete a folder. Files in it become unsorted."""
    try:
        await fs_db.delete_folder(folder_id)
        return {"status": "success", "message": f"Folder {folder_id} deleted"}
    except Exception as e:
        logger.error(f"Failed to delete folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/files/move")
async def move_file(request: FileMoveRequest):
    """Move a file to a folder (or None for unsorted)."""
    try:
        await fs_db.move_file_to_folder(request.document_id, request.filename, request.folder_id)
        return {"status": "success", "document_id": request.document_id, "filename": request.filename, "folder_id": request.folder_id}
    except Exception as e:
        logger.error(f"Failed to move file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/unsorted")
async def get_unsorted_files():
    """Get all files that are not assigned to any folder."""
    try:
        # Get all documents from vector DB (each has unique document_id)
        all_docs = await vector_db.list_documents()
        
        # Get unsorted files (compares by document_id)
        unsorted_docs = await fs_db.get_unsorted_files(all_docs)
        
        # Return {document_id, filename} objects for frontend
        return [{"document_id": doc.get("id"), "filename": doc.get("filename")} for doc in unsorted_docs]
    except Exception as e:
        logger.error(f"Failed to get unsorted files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/in_folders")
async def get_files_in_folders():
    """Get a mapping of folder_id -> [filenames]."""
    try:
        files_map = await fs_db.get_files_in_folders()
        return files_map
    except Exception as e:
        logger.error(f"Failed to get files in folders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/content/{filename}")
async def get_file_content(filename: str):
    """Get the content of a file."""
    try:
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
            
        return FileResponse(file_path)
    except Exception as e:
        logger.error(f"Failed to get file content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 3D Visualization Endpoints ====================

class Point3D(BaseModel):
    id: str
    filename: Optional[str] = None
    coordinates: List[float]
    cluster: Optional[int] = None

class Embeddings3DResponse(BaseModel):
    method: str
    points: List[Point3D]

@app.get("/api/embeddings/3d", response_model=Embeddings3DResponse)
async def get_embeddings_3d(cluster: Optional[str] = None):
    """Get all embeddings reduced to 3D coordinates, optionally filtered by cluster"""
    global _3d_cache
    
    try:
        # Check if cache is valid
        if not _3d_cache["is_valid"]:
            logger.info("3D cache miss - building cache...")
            
            # Get all data from vector DB (slow, one time)
            all_data = await vector_db.get_all_embeddings()
            
            if not all_data:
                return Embeddings3DResponse(method=dim_reducer.method, points=[])
            
            # Extract vectors
            embeddings = [item['vector'] for item in all_data]
            
            # Fit PCA if needed (slow, one time)
            if not dim_reducer.is_fitted:
                logger.info("Fitting PCA model on all data...")
                dim_reducer.fit_transform(embeddings)
                logger.info(f"PCA fitted on {len(embeddings)} vectors")
            
            # Transform all to 3D
            coords_3d = dim_reducer.transform(embeddings)
            
            # Cache results
            _3d_cache["coords"] = coords_3d
            _3d_cache["point_ids"] = [item['id'] for item in all_data]
            _3d_cache["metadata"] = [item.get('metadata', {}) for item in all_data]
            _3d_cache["is_valid"] = True
            logger.info("3D cache built successfully")
        
        # Use cached data (fast!)
        coords_3d = _3d_cache["coords"]
        point_ids = _3d_cache["point_ids"]
        metadata_list = _3d_cache["metadata"]
        
        # Filter by cluster (instant!)
        points = []
        for i, metadata in enumerate(metadata_list):
            if cluster and cluster != FILTER_ALL:
                try:
                    if metadata.get('cluster') != int(cluster):
                        continue
                except ValueError:
                    pass
            
            points.append(Point3D(
                id=str(point_ids[i]),
                filename=metadata.get('filename') or metadata.get('course_name'),
                coordinates=coords_3d[i].tolist(),
                cluster=metadata.get('cluster')
            ))
        
        return Embeddings3DResponse(method=dim_reducer.method, points=points)
        
    except Exception as e:
        logger.error(f"Failed to get 3D embeddings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class Query3DRequest(BaseModel):
    query: str
    cluster_filter: Optional[str] = None

class Neighbor3D(BaseModel):
    id: str
    filename: Optional[str] = None
    coordinates: List[float]
    similarity: float

class Query3DResponse(BaseModel):
    query_coordinates: List[float]
    top_k_neighbors: List[Neighbor3D]

@app.post("/api/embeddings/3d/query", response_model=Query3DResponse)
async def transform_query_3d(request: Query3DRequest):
    """Transform a query string to 3D coordinates and find neighbors"""
    try:
        # 1. Get query embedding
        query_vector = await embedding_service.embed_text_async(request.query)
        
        # 2. Transform to 3D
        if not dim_reducer.is_fitted:
            # Try to fit if we have data
            all_data = await vector_db.get_all_embeddings()
            if all_data:
                embeddings = [item['vector'] for item in all_data]
                dim_reducer.fit_transform(embeddings)
            else:
                return Query3DResponse(
                    query_coordinates=[0.0, 0.0, 0.0],
                    top_k_neighbors=[]
                )
                
        query_coords = dim_reducer.transform(query_vector)[0].tolist()
        
        # 3. Find neighbors
        search_filters = None
        if request.cluster_filter and request.cluster_filter != FILTER_ALL:
            try:
                search_filters = {"cluster": int(request.cluster_filter)}
            except ValueError:
                pass

        results = await vector_db.search(query_vector, limit=10, filter_criteria=search_filters)
        
        # 4. Get 3D coords for neighbors
        neighbor_ids = [hit['id'] for hit in results]
        neighbor_vectors_data = await vector_db.get_vectors_by_ids(neighbor_ids)
        
        # Map ID to vector data
        neighbor_map = {item['id']: item for item in neighbor_vectors_data}
        
        neighbors = []
        for hit in results:
            hit_id = hit['id']
            if hit_id in neighbor_map:
                vec_data = neighbor_map[hit_id]
                # Transform neighbor vector to 3D
                # Note: In a real app, we might want to cache these or lookup in the bulk transform
                # But transforming a few points is fast enough
                neighbor_3d = dim_reducer.transform(vec_data['vector'])[0].tolist()
                
                neighbors.append(Neighbor3D(
                    id=str(hit_id),
                    filename=hit['metadata'].get('filename') or hit['metadata'].get('course_name'),
                    coordinates=neighbor_3d,
                    similarity=hit['score']
                ))
                
        return Query3DResponse(
            query_coordinates=query_coords,
            top_k_neighbors=neighbors
        )
            
    except Exception as e:
        logger.error(f"Failed to query 3D embeddings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cluster")
async def cluster_documents(background_tasks: BackgroundTasks):
    """
    Run HDBSCAN clustering on all individual chunks and update metadata.
    Returns immediately with a job_id for status polling.
    """
    job_id = str(uuid.uuid4())
    create_job(job_id, JobType.CLUSTERING)
    
    # Start clustering in background
    background_tasks.add_task(run_clustering_job, job_id)
    
    return {
        "job_id": job_id,
        "status": "started",
        "message": "Clustering job started. Use /api/jobs/{job_id} to check status."
    }


async def run_clustering_job(job_id: str):
    """Background task to run clustering."""
    try:
        update_job(job_id, status=JobStatus.RUNNING, progress=0)
        
        # Get all embeddings
        all_data = await vector_db.get_all_embeddings()
        
        if not all_data:
            update_job(job_id, status=JobStatus.COMPLETED, progress=100, result={
                "message": "No documents to cluster",
                "clusters": 0
            })
            return

        update_job(job_id, progress=10)
        
        embeddings = [item['vector'] for item in all_data]
        total_chunks = len(embeddings)
        
        # Adjust min_cluster_size based on total chunks
        if total_chunks < 50:
            clustering_service.min_cluster_size = 3
        elif total_chunks < 200:
            clustering_service.min_cluster_size = 5
        else:
            clustering_service.min_cluster_size = 10
            
        # Cluster individual chunks
        cluster_ids = clustering_service.fit_predict(embeddings)
        update_job(job_id, progress=40)
        
        # Generate cluster names
        cluster_names = clustering_service.generate_cluster_names(all_data, cluster_ids)
        update_job(job_id, progress=50)
        
        # Update each point's metadata in Qdrant
        total_items = len(all_data)
        for i, item in enumerate(all_data):
            point_id = item['id']
            cluster_id = int(cluster_ids[i])
            cluster_name = cluster_names.get(cluster_id, f"Cluster {cluster_id}")
            
            await vector_db.client.set_payload(
                collection_name=vector_db.collection_name,
                points=[point_id],
                payload={
                    'cluster': cluster_id,
                    'cluster_name': cluster_name
                }
            )
            
            # Update progress (50-90%)
            if i % 10 == 0:  # Update every 10 items to avoid overhead
                progress = 50 + int((i / total_items) * 40)
                update_job(job_id, progress=progress)
            
        # Calculate stats
        n_clusters = len(set(cluster_ids)) - (1 if -1 in cluster_ids else 0)
        n_noise = list(cluster_ids).count(-1)
        
        # Count unique documents involved
        unique_filenames = set()
        for item in all_data:
            metadata = item.get('metadata', {})
            filename = metadata.get('filename')
            if filename:
                unique_filenames.add(filename)
        
        logger.info(f"Clustered {total_chunks} chunks into {n_clusters} groups (Noise: {n_noise})")
        
        # Invalidate 3D cache since cluster metadata changed
        invalidate_3d_cache()
        
        result = {
            "message": "Clustering complete",
            "total_documents": len(unique_filenames),
            "total_chunks": total_chunks,
            "clusters": n_clusters,
            "noise_points": n_noise,
            "cluster_names": cluster_names
        }
        
        update_job(job_id, status=JobStatus.COMPLETED, progress=100, result=result)

    except Exception as e:
        logger.error(f"Clustering job {job_id} failed: {e}")
        update_job(job_id, status=JobStatus.FAILED, error=str(e))


# ==================== Job Status Endpoints ====================

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of a background job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/api/jobs")
async def list_all_jobs(job_type: Optional[str] = None):
    """List all recent jobs, optionally filtered by type."""
    try:
        type_filter = JobType(job_type) if job_type else None
        jobs = list_jobs(type_filter)
        return {"jobs": jobs}
    except ValueError:
        return {"jobs": list_jobs()}

@app.get("/api/clusters")
async def get_clusters():
    """Get all unique cluster IDs and names."""
    try:
        all_data = await vector_db.get_all_embeddings()
        clusters = {} # id -> name
        
        for item in all_data:
            metadata = item.get('metadata', {})
            if 'cluster' in metadata:
                c_id = metadata['cluster']
                c_name = metadata.get('cluster_name', f"Cluster {c_id}")
                clusters[c_id] = c_name
        
        # Convert to list of objects
        cluster_list = []
        for c_id, c_name in clusters.items():
            cluster_list.append({"id": c_id, "name": c_name})
            
        # Sort by ID
        cluster_list.sort(key=lambda x: x['id'])
        
        return {"clusters": cluster_list}
    except Exception as e:
        logger.error(f"Failed to get clusters: {e}")
        raise HTTPException(status_code=500, detail=str(e))

import zipfile
from io import BytesIO
from fastapi.responses import StreamingResponse

@app.get("/export")
async def export_data():
    """Export all uploaded data as a ZIP file with folder structure."""
    logger.info("Exporting data with folder structure...")
    try:
        # 1. Get all folders and build path map
        folders = await fs_db.get_all_folders()
        
        # Helper to build full paths
        folder_map = {} # id -> full_path
        folders_by_id = {f['id']: f for f in folders}
        
        def get_path(folder_id):
            if folder_id in folder_map:
                return folder_map[folder_id]
            
            folder = folders_by_id.get(folder_id)
            if not folder:
                return None
            
            if folder['parent_id'] is None:
                path = folder['name']
            else:
                parent_path = get_path(folder['parent_id'])
                if parent_path:
                    path = f"{parent_path}/{folder['name']}"
                else:
                    path = folder['name']
            
            folder_map[folder_id] = path
            return path

        # Build map for all folders
        for folder in folders:
            get_path(folder['id'])
            
        # 2. Get file mappings
        files_map = await fs_db.get_files_in_folders() # folder_id -> [filenames]
        
        # Invert map for easier lookup: filename -> folder_id
        file_to_folder = {}
        for folder_id, filenames in files_map.items():
            for fname in filenames:
                file_to_folder[fname] = folder_id

        # 3. Create ZIP in memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Iterate through all files in uploads dir
            if os.path.exists(settings.UPLOAD_DIR):
                for filename in os.listdir(settings.UPLOAD_DIR):
                    file_path = os.path.join(settings.UPLOAD_DIR, filename)
                    if os.path.isfile(file_path):
                        # Determine archive name (path inside zip)
                        folder_id = file_to_folder.get(filename)
                        
                        if folder_id and folder_id != FOLDER_NULL:
                            # File is in a folder
                            folder_path = folder_map.get(folder_id)
                            if folder_path:
                                arcname = f"{folder_path}/{filename}"
                            else:
                                # Fallback if folder not found
                                arcname = f"{FOLDER_UNSORTED}/{filename}"
                        elif folder_id == FOLDER_NULL:
                            # File is at root
                            arcname = filename
                        else:
                            # File is unsorted
                            arcname = f"unsorted/{filename}"
                            
                        zip_file.write(file_path, arcname)

        # 4. Return as streaming response
        zip_buffer.seek(0)
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=data_export.zip"}
        )

    except Exception as e:
        logger.error(f"Failed to export data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =======================================================================
# MCP-ONLY ENDPOINTS
# These endpoints are designed for AI agent (MCP) use only, not frontend.
# =======================================================================

class MCPDocumentRequest(BaseModel):
    """Request model for MCP document creation"""
    filename: str
    content: str
    folder_id: Optional[str] = None

class MCPDocumentResponse(BaseModel):
    """Response model for MCP document creation"""
    status: str
    document_id: str
    filename: str
    chunks_created: int
    message: str

# Allowed extensions for MCP text document creation
MCP_ALLOWED_EXTENSIONS = {".txt", ".md", ".json"}
MCP_MAX_CONTENT_SIZE = 102400  # 100KB

@app.post("/mcp/create-document", response_model=MCPDocumentResponse)
async def mcp_create_document(request: MCPDocumentRequest):
    """
    Create a text document from string content.
    
    MCP-ONLY endpoint - designed for AI agent use, not frontend.
    Accepts plain text/markdown content and processes it through the 
    embedding pipeline without requiring binary file uploads.
    """
    from chunker import chunker
    
    filename = request.filename.strip()
    content = request.content
    folder_id = request.folder_id
    
    # Validation: filename extension
    ext = os.path.splitext(filename)[1].lower()
    if ext not in MCP_ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file extension. Allowed: {', '.join(MCP_ALLOWED_EXTENSIONS)}"
        )
    
    # Validation: filename length
    if len(filename) > 255:
        raise HTTPException(status_code=400, detail="Filename too long (max 255 characters)")
    
    # Validation: content not empty
    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    
    # Validation: content size
    if len(content) > MCP_MAX_CONTENT_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"Content too large. Maximum size: {MCP_MAX_CONTENT_SIZE // 1024}KB"
        )
    
    # Validation: folder exists if provided
    if folder_id:
        folders = await fs_db.get_all_folders()
        folder_ids = {f['id'] for f in folders}
        if folder_id not in folder_ids:
            raise HTTPException(status_code=400, detail=f"Folder {folder_id} not found")
    
    logger.info(f"MCP creating document: {filename}")
    
    try:
        # Generate document ID
        document_id = str(uuid.uuid4())
        upload_timestamp = time.time()  # Unix timestamp (float)
        
        # Write physical file to uploads directory
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Prepare metadata
        metadata = {
            "filename": filename,
            "document_id": document_id,
            "source": "mcp",  # Mark as MCP-created
            "upload_date": upload_timestamp,
        }
        
        # Chunk the content
        chunks = chunker.chunk_text(content, metadata)
        
        if not chunks:
            raise HTTPException(status_code=400, detail="Could not process content into chunks")
        
        # Extract just the text for embedding
        chunk_texts = [c['text'] for c in chunks]
        
        # Generate embeddings
        embeddings = await embedding_service.embed_batch_async(chunk_texts)
        
        # Prepare points for Qdrant
        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = str(uuid.uuid4())
            payload = {
                "text": chunk['text'],
                "filename": filename,
                "document_id": document_id,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "source": "mcp",
                "upload_date": metadata["upload_date"],
            }
            points.append({
                "id": point_id,
                "vector": embedding.tolist() if hasattr(embedding, 'tolist') else embedding,
                "payload": payload
            })
        
        # Store in Qdrant
        await vector_db.upsert_batch(points)
        
        # Register in document registry
        document_registry.register(document_id, {
            "filename": filename,
            "upload_date": metadata["upload_date"],
            "total_chunks": len(chunks),
            "source": "mcp",
        })
        
        # Assign to folder if specified
        if folder_id:
            await fs_db.move_file_to_folder(document_id, filename, folder_id)
        
        # Invalidate 3D cache since we added new data
        invalidate_3d_cache()
        
        logger.info(f"MCP document created: {filename} ({len(chunks)} chunks)")
        
        return MCPDocumentResponse(
            status="success",
            document_id=document_id,
            filename=filename,
            chunks_created=len(chunks),
            message="Document created via MCP"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCP document creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create document: {str(e)}")


@app.delete("/reset")
@limiter.limit(settings.RATE_LIMIT_RESET)
async def reset_data(
    request: Request,  # Required for rate limiting
    admin_key: str = Header(None, alias="X-Admin-Key")
):
    """Reset the entire database and delete all files. Requires admin key if configured."""
    # Check admin key if configured
    if settings.ADMIN_KEY and admin_key != settings.ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing admin key")
    
    logger.info("Resetting data...")
    try:
        # 1. Reset Qdrant collection
        await vector_db.reset_collection()
        
        # 2. Reset filesystem DB
        await fs_db.reset_db()
        
        # 3. Delete all files in uploads directory (but keep the directory itself for Docker volume)
        if os.path.exists(settings.UPLOAD_DIR):
            for filename in os.listdir(settings.UPLOAD_DIR):
                file_path = os.path.join(settings.UPLOAD_DIR, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    logger.error(f'Failed to delete {file_path}: {e}')
            
        # 4. Reset dimensionality reducer
        global dim_reducer
        dim_reducer = DimensionalityReducer(method='pca', n_components=3)
        
        # 5. Invalidate 3D cache
        invalidate_3d_cache()
        
        return {"status": "success", "message": "All data has been reset"}
    except Exception as e:
        logger.error(f"Failed to reset data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logger.info("Starting Vector Database API server...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


