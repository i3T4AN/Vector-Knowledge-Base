# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         MCP Server configuration and setup
# =======================================================================

"""
Model Context Protocol (MCP) server integration.
Exposes FastAPI endpoints as MCP tools for AI agent consumption.
"""

import logging
from typing import Optional, Set
from fastapi import FastAPI

from config import settings

logger = logging.getLogger(__name__)


# =======================================================================
# MCP Operation Lists
# =======================================================================

# Operations to EXCLUDE from MCP (dangerous, unsupported, or sensitive)
EXCLUDED_OPERATIONS: Set[str] = {
    # Destructive operations
    "reset_data_reset_delete",
    
    # File uploads (require binary data - not supported via MCP)
    "upload_file_upload_post",
    "upload_folder_batch_upload_batch_post",
    
    # Large file exports (not practical for MCP)
    "export_data_export_get",
}

# Operations to INCLUDE in MCP (core safe functionality)
INCLUDED_OPERATIONS: Set[str] = {
    # Health & Config
    "health_check_health_get",
    "get_allowed_extensions_config_allowed_extensions_get",
    
    # Search
    "search_documents_search_post",
    
    # Document Management
    "list_documents_documents_get",
    "delete_document_documents__filename__delete",
    
    # Folder Management
    "get_folders_folders_get",
    "create_folder_folders_post",
    "update_folder_folders__folder_id__put",
    "delete_folder_folders__folder_id__delete",
    
    # File Operations
    "move_file_files_move_post",
    "get_unsorted_files_files_unsorted_get",
    "get_files_in_folders_files_in_folders_get",
    
    # Clustering & Visualization
    "cluster_documents_api_cluster_post",
    "get_clusters_api_clusters_get",
    "get_embeddings_3d_api_embeddings_3d_get",
    "transform_query_3d_api_embeddings_3d_query_post",
    
    # Jobs
    "get_job_status_api_jobs__job_id__get",
    
    # MCP Document Creation (AI agent only)
    "mcp_create_document_mcp_create_document_post",
}


def setup_mcp_server(app: FastAPI) -> Optional[object]:
    """
    Initialize and configure MCP server.
    
    Returns None if MCP is disabled in settings or if fastapi-mcp is not available.
    """
    if not settings.MCP_ENABLED:
        logger.info("MCP server is disabled via MCP_ENABLED setting")
        return None
    
    try:
        from fastapi_mcp import FastApiMCP
    except ImportError:
        logger.warning("fastapi-mcp package not installed. MCP server disabled.")
        logger.warning("Install with: pip install fastapi-mcp")
        return None
    
    logger.info(f"Initializing MCP server at path: {settings.MCP_PATH}")
    
    try:
        # Note: FastApiMCP only supports one of include_operations OR exclude_operations.
        # Using exclude_operations (blacklist) is more robust - it exposes all endpoints
        # except the explicitly blocked ones, so new endpoints are automatically available.
        mcp = FastApiMCP(
            app,
            name=settings.MCP_NAME,
            description="AI-powered vector database for semantic document search, "
                        "clustering, and knowledge management. Supports PDF, DOCX, "
                        "PPTX, images (OCR), code files, and more.",
            exclude_operations=list(EXCLUDED_OPERATIONS),
        )
        
        # Mount MCP at configured path
        mcp.mount(mount_path=settings.MCP_PATH)
        
        logger.info(f"MCP server initialized successfully at {settings.MCP_PATH}")
        logger.info(f"Included: {len(INCLUDED_OPERATIONS)} operations")
        logger.info(f"Excluded: {len(EXCLUDED_OPERATIONS)} operations")
        
        return mcp
        
    except Exception as e:
        logger.error(f"Failed to initialize MCP server: {e}")
        return None
