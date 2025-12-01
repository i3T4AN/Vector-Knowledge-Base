# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         FastAPI application and API endpoints
# =======================================================================

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import uvicorn
import os
import shutil
import numpy as np

# Import backend modules
from config import settings
from ingestion import ingestion_service
from embedding_service import embedding_service
from vector_db import vector_db
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Vector Database API",
    description="A vector database application for course material and projects",
    version="1.0.0"
)

# Initialize Dimensionality Reducer
dim_reducer = DimensionalityReducer(method='pca', n_components=3)

# Initialize Clustering Service
clustering_service = ClusteringService(min_cluster_size=5)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Startup event to initialize databases
@app.on_event("startup")
async def startup_event():
    """Initialize databases on startup"""
    logger.info("Initializing databases on startup...")
    try:
        # Ensure Qdrant collection exists
        vector_db.ensure_collection()
        logger.info("Qdrant collection initialized")
        
        # Initialize and fit dimensionality reducer
        logger.info("Fitting dimensionality reducer...")
        all_data = vector_db.get_all_embeddings()
        if all_data:
            embeddings = [item['vector'] for item in all_data]
            dim_reducer.fit_transform(embeddings)
            logger.info(f"Dimensionality reducer fitted on {len(embeddings)} embeddings")
        else:
            logger.warning("No embeddings found, skipping dimensionality reducer fit")
            
    except Exception as e:
        logger.error(f"Failed to initialize databases: {e}")
        raise

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
    cluster_filter: Optional[str] = None  # New field

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

@app.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """
    Search for documents using vector similarity.
    """
    logger.info(f"Received search request: {request.query}")
    
    # 1. Generate embedding for the query
    try:
        query_vector = embedding_service.embed_text(request.query)
    except Exception as e:
        raise EmbeddingError(f"Failed to embed query: {e}")
    
    # 2. Search in Vector DB
    try:
        # Handle cluster filtering
        search_filters = request.filters or {}
        if request.cluster_filter and request.cluster_filter != "all":
            try:
                search_filters["cluster"] = int(request.cluster_filter)
            except ValueError:
                pass # Ignore invalid cluster IDs

        results = vector_db.search(
            query_vector=query_vector,
            limit=request.limit,
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
        documents = vector_db.list_documents()
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
        vector_db.delete_document("filename", filename)
        
        # 3. Remove from file system organization
        fs_db.remove_file(filename)
        
        return {"status": "success", "message": f"Document {filename} deleted"}
    except Exception as e:
        logger.error(f"Failed to delete document: {str(e)}")
        raise VectorDBError(f"Failed to delete document: {str(e)}")

@app.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    category: str = Form(...),
    tags: Optional[str] = Form(None),
    relative_path: Optional[str] = Form(None)  # NEW: folder path
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
            target_folder_id = fs_db.get_or_create_folder_path(path_components)
            logger.info(f"Created/found folder structure, target folder ID: {target_folder_id}")
    
    # Move file to the target folder
    if target_folder_id:
        fs_db.move_file_to_folder(result["filename"], target_folder_id)
        logger.info(f"Moved {result['filename']} to folder {target_folder_id}")
    elif relative_path is not None:
        # relative_path was provided but empty, move to Root
        fs_db.move_file_to_folder(result["filename"], None)
    # else: file remains unsorted (default behavior)
    
    return UploadResponse(
        file_id=result.get("file_id", "unknown"),
        filename=result["filename"],
        status=result["status"],
        chunks_count=result.get("chunks_count", 0),
        document_id=result.get("document_id", ""),
        message=result.get("message")
    )

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
    filename: str
    folder_id: Optional[str] = None

@app.get("/folders")
async def get_folders():
    """Get all folders."""
    try:
        folders = fs_db.get_all_folders()
        return folders
    except Exception as e:
        logger.error(f"Failed to get folders: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/folders")
async def create_folder(folder: FolderCreate):
    """Create a new folder."""
    try:
        folder_id = fs_db.create_folder(folder.name, folder.parent_id)
        return {"id": folder_id, "name": folder.name, "parent_id": folder.parent_id}
    except Exception as e:
        logger.error(f"Failed to create folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/folders/{folder_id}")
async def update_folder(folder_id: str, folder: FolderUpdate):
    """Update a folder's name or move it to a new parent."""
    try:
        fs_db.update_folder(folder_id, folder.name, folder.parent_id)
        return {"status": "success", "folder_id": folder_id}
    except Exception as e:
        logger.error(f"Failed to update folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/folders/{folder_id}")
async def delete_folder(folder_id: str):
    """Delete a folder. Files in it become unsorted."""
    try:
        fs_db.delete_folder(folder_id)
        return {"status": "success", "message": f"Folder {folder_id} deleted"}
    except Exception as e:
        logger.error(f"Failed to delete folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/files/move")
async def move_file(request: FileMoveRequest):
    """Move a file to a folder (or None for unsorted)."""
    try:
        fs_db.move_file_to_folder(request.filename, request.folder_id)
        return {"status": "success", "filename": request.filename, "folder_id": request.folder_id}
    except Exception as e:
        logger.error(f"Failed to move file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/unsorted")
async def get_unsorted_files():
    """Get all files that are not assigned to any folder."""
    try:
        # Get all document filenames from vector DB
        all_docs = vector_db.list_documents()
        all_filenames = [doc.get("filename") for doc in all_docs]
        
        # Get unsorted files
        unsorted = fs_db.get_unsorted_files(all_filenames)
        return unsorted
    except Exception as e:
        logger.error(f"Failed to get unsorted files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/in_folders")
async def get_files_in_folders():
    """Get a mapping of folder_id -> [filenames]."""
    try:
        files_map = fs_db.get_files_in_folders()
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
    try:
        # Get all data from vector DB
        all_data = vector_db.get_all_embeddings()
        
        if not all_data:
            return Embeddings3DResponse(method=dim_reducer.method, points=[])
            
        # Extract vectors for transformation
        embeddings = [item['vector'] for item in all_data]
        
        # Ensure model is fitted
        if not dim_reducer.is_fitted:
            dim_reducer.fit_transform(embeddings)
            
        # Transform to 3D
        coords_3d = dim_reducer.transform(embeddings)
        
        points = []
        for i, item in enumerate(all_data):
            metadata = item.get('metadata', {})
            
            # Filter by cluster if specified
            if cluster and cluster != "all":
                try:
                    cluster_id = int(cluster)
                    if metadata.get('cluster') != cluster_id:
                        continue
                except ValueError:
                    pass # Ignore invalid cluster filter

            points.append(Point3D(
                id=str(item['id']),
                filename=metadata.get('filename') or metadata.get('course_name'),
                coordinates=coords_3d[i].tolist(),
                cluster=metadata.get('cluster')
            ))
            
        return Embeddings3DResponse(
            method=dim_reducer.method,
            points=points
        )
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
        query_vector = embedding_service.embed_text(request.query)
        
        # 2. Transform to 3D
        if not dim_reducer.is_fitted:
            # Try to fit if we have data
            all_data = vector_db.get_all_embeddings()
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
        if request.cluster_filter and request.cluster_filter != "all":
            try:
                search_filters = {"cluster": int(request.cluster_filter)}
            except ValueError:
                pass

        results = vector_db.search(query_vector, limit=10, filter_criteria=search_filters)
        
        # 4. Get 3D coords for neighbors
        neighbor_ids = [hit['id'] for hit in results]
        neighbor_vectors_data = vector_db.get_vectors_by_ids(neighbor_ids)
        
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
async def cluster_documents():
    """
    Run HDBSCAN clustering on all individual chunks and update metadata.
    """
    try:
        # Get all embeddings
        all_data = vector_db.get_all_embeddings()
        
        if not all_data:
             return {"message": "No documents to cluster", "clusters": 0}

        embeddings = [item['vector'] for item in all_data]
        total_chunks = len(embeddings)
        
        # Adjust min_cluster_size based on total chunks
        # For chunks, we generally want a slightly higher minimum to avoid noise
        if total_chunks < 50:
            clustering_service.min_cluster_size = 3
        elif total_chunks < 200:
            clustering_service.min_cluster_size = 5
        else:
            clustering_service.min_cluster_size = 10
            
        # Cluster individual chunks
        cluster_ids = clustering_service.fit_predict(embeddings)
        
        # Generate cluster names
        cluster_names = clustering_service.generate_cluster_names(all_data, cluster_ids)
        
        # Update each point's metadata in Qdrant
        for i, item in enumerate(all_data):
            point_id = item['id']
            cluster_id = int(cluster_ids[i])
            cluster_name = cluster_names.get(cluster_id, f"Cluster {cluster_id}")
            
            # Update the point in Qdrant
            vector_db.client.set_payload(
                collection_name=vector_db.collection_name,
                points=[point_id],
                payload={
                    'cluster': cluster_id,
                    'cluster_name': cluster_name
                }
            )
            
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
        
        return {
            "message": "Clustering complete",
            "total_documents": len(unique_filenames),
            "total_chunks": total_chunks,
            "clusters": n_clusters,
            "noise_points": n_noise,
            "cluster_names": cluster_names
        }

    except Exception as e:
        logger.error(f"Clustering failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/clusters")
async def get_clusters():
    """Get all unique cluster IDs and names."""
    try:
        all_data = vector_db.get_all_embeddings()
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
        folders = fs_db.get_all_folders()
        
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
        files_map = fs_db.get_files_in_folders() # folder_id -> [filenames]
        
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
                        
                        if folder_id and folder_id != "null":
                            # File is in a folder
                            folder_path = folder_map.get(folder_id)
                            if folder_path:
                                arcname = f"{folder_path}/{filename}"
                            else:
                                # Fallback if folder not found
                                arcname = f"unsorted/{filename}"
                        elif folder_id == "null":
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

@app.delete("/reset")
async def reset_data():
    """Reset the entire database and delete all files."""
    logger.info("Resetting data...")
    try:
        # 1. Reset Qdrant collection
        vector_db.reset_collection()
        
        # 2. Reset filesystem DB
        fs_db.reset_db()
        
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


