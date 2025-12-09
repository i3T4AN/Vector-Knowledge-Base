# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         File system database operations (async)
# =======================================================================

"""
Database module for the file system organization layer.
Manages folders and file-to-folder mappings using SQLite with async operations.
"""
import aiosqlite
import sqlite3
import uuid
from typing import List, Dict, Optional
import logging
from constants import FOLDER_NULL

logger = logging.getLogger(__name__)


class FileSystemDB:
    def __init__(self, db_path: str = "metadata.db"):
        self.db_path = db_path
        # Sync init to create tables on startup
        self._init_db_sync()
    
    def _init_db_sync(self):
        """Initialize the database with required tables (sync, called once at startup)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Enable WAL mode for better concurrency
        cursor.execute("PRAGMA journal_mode=WAL")
        
        # Folders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS folders (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                parent_id TEXT,
                FOREIGN KEY (parent_id) REFERENCES folders(id) ON DELETE CASCADE
            )
        """)
        
        # File-to-folder mapping table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_folders (
                document_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                folder_id TEXT,
                FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE SET NULL
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("File system database initialized (WAL mode enabled)")
    
    async def get_all_folders(self) -> List[Dict]:
        """Get all folders."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT id, name, parent_id FROM folders") as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """Create a new folder."""
        folder_id = str(uuid.uuid4())
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO folders (id, name, parent_id) VALUES (?, ?, ?)",
                (folder_id, name, parent_id)
            )
            await db.commit()
        logger.info(f"Created folder: {name} (ID: {folder_id}, Parent: {parent_id})")
        return folder_id
    
    async def update_folder(self, folder_id: str, name: Optional[str] = None, parent_id: Optional[str] = None):
        """Update a folder's name or parent."""
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        
        if parent_id is not None:
            updates.append("parent_id = ?")
            params.append(parent_id)
        
        if updates:
            params.append(folder_id)
            query = f"UPDATE folders SET {', '.join(updates)} WHERE id = ?"
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(query, params)
                await db.commit()
        logger.info(f"Updated folder ID: {folder_id}")
    
    async def delete_folder(self, folder_id: str):
        """Delete a folder. Files in it become unsorted."""
        async with aiosqlite.connect(self.db_path) as db:
            # Remove file associations (files become unsorted)
            await db.execute("DELETE FROM file_folders WHERE folder_id = ?", (folder_id,))
            # Delete the folder
            await db.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
            await db.commit()
        logger.info(f"Deleted folder ID: {folder_id}")
    
    async def move_file_to_folder(self, document_id: str, filename: str, folder_id: Optional[str]):
        """Assign a file to a folder. folder_id='unsorted' removes mapping. None=Root."""
        async with aiosqlite.connect(self.db_path) as db:
            if folder_id == 'unsorted':
                # Moving to unsorted: DELETE the entry entirely
                await db.execute("DELETE FROM file_folders WHERE document_id = ?", (document_id,))
                logger.info(f"Moved {filename} (doc:{document_id}) to unsorted")
            else:
                # Moving to a folder (or Root if None): INSERT or UPDATE
                async with db.execute("SELECT document_id FROM file_folders WHERE document_id = ?", (document_id,)) as cursor:
                    exists = await cursor.fetchone()
                
                if exists:
                    await db.execute(
                        "UPDATE file_folders SET folder_id = ?, filename = ? WHERE document_id = ?",
                        (folder_id, filename, document_id)
                    )
                else:
                    await db.execute(
                        "INSERT INTO file_folders (document_id, filename, folder_id) VALUES (?, ?, ?)",
                        (document_id, filename, folder_id)
                    )
                logger.info(f"Moved {filename} (doc:{document_id}) to folder {folder_id}")
            await db.commit()
    
    async def get_files_in_folders(self) -> Dict[str, List[Dict]]:
        """Get a mapping of folder_id -> [{document_id, filename}, ...]."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT document_id, filename, folder_id FROM file_folders") as cursor:
                rows = await cursor.fetchall()
        
        # Build mapping
        result = {}
        for document_id, filename, folder_id in rows:
            key = str(folder_id) if folder_id is not None else FOLDER_NULL
            if key not in result:
                result[key] = []
            result[key].append({"document_id": document_id, "filename": filename})
        
        return result
    
    async def get_unsorted_files(self, all_docs: List[Dict]) -> List[Dict]:
        """
        Get files that are not assigned to any folder.
        all_docs: List of document dicts with 'id' (document_id) and 'filename'.
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT document_id FROM file_folders") as cursor:
                rows = await cursor.fetchall()
                sorted_doc_ids = {row[0] for row in rows}
        
        # Return docs that are not in the sorted set
        unsorted = [doc for doc in all_docs if doc.get('id') not in sorted_doc_ids]
        return unsorted
    
    async def remove_file(self, document_id: str):
        """Remove a file from the file system (called when document is deleted)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM file_folders WHERE document_id = ?", (document_id,))
            await db.commit()
        logger.info(f"Removed document {document_id} from file system")

    async def get_or_create_folder_path(self, path_components: List[str]) -> str:
        """
        Get or create a folder path from a list of folder names.
        
        Args:
            path_components: List of folder names in order, e.g., ['schoolwork', 'senior year', 'math']
        
        Returns:
            The ID of the final folder in the path
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            current_parent_id = None  # Start at root
            
            for folder_name in path_components:
                # Check if folder exists under current parent
                if current_parent_id is None:
                    async with db.execute(
                        "SELECT id FROM folders WHERE name = ? AND parent_id IS NULL",
                        (folder_name,)
                    ) as cursor:
                        result = await cursor.fetchone()
                else:
                    async with db.execute(
                        "SELECT id FROM folders WHERE name = ? AND parent_id = ?",
                        (folder_name, current_parent_id)
                    ) as cursor:
                        result = await cursor.fetchone()
                
                if result:
                    # Folder exists, use it
                    current_parent_id = result[0]
                    logger.info(f"Found existing folder: {folder_name} (ID: {current_parent_id})")
                else:
                    # Folder doesn't exist, create it
                    folder_id = str(uuid.uuid4())
                    await db.execute(
                        "INSERT INTO folders (id, name, parent_id) VALUES (?, ?, ?)",
                        (folder_id, folder_name, current_parent_id)
                    )
                    await db.commit()
                    current_parent_id = folder_id
                    logger.info(f"Created folder: {folder_name} (ID: {folder_id}, Parent: {current_parent_id})")
            
            return current_parent_id

    async def reset_db(self):
        """Reset the database by clearing all tables."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM file_folders")
            await db.execute("DELETE FROM folders")
            await db.commit()
        logger.info("File system database reset")


# Global instance
fs_db = FileSystemDB()
