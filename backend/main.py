# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         FastAPI application and API endpoints
# =======================================================================

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import uvicorn
import os
import shutil

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
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant collection: {e}")
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
        results = vector_db.search(
            query_vector=query_vector,
            limit=request.limit,
            filter_criteria=request.filters
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
    course_name: str = Form(...),
    document_type: Optional[str] = Form(None),
    tags: Optional[str] = Form(None)
):
    """
    Upload a file to the vector database.
    """
    logger.info(f"Received upload request for {file.filename}")
    
    # Validate file extension
    _, ext = os.path.splitext(file.filename)
    if ext.lower() not in settings.ALLOWED_EXTENSIONS:
        logger.warning(f"Rejected file {file.filename} with extension {ext}")
        raise InvalidFileFormatError(f"File type '{ext}' not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}")
    
    # Prepare metadata
    metadata = {
        "course_name": course_name,
        "document_type": document_type or "uncategorized"
    }
    
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        metadata["tags"] = tag_list
        
    # Process file (IngestionService now raises exceptions)
    result = await ingestion_service.process_file(file, extra_metadata=metadata)
    
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

if __name__ == "__main__":
    logger.info("Starting Vector Database API server...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


