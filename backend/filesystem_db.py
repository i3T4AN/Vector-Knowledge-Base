# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         File system database operations
# =======================================================================

"""
Database module for the file system organization layer.
Manages folders and file-to-folder mappings using SQLite.
"""
import sqlite3
import uuid
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class FileSystemDB:
    def __init__(self, db_path: str = "metadata.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize the database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
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
                filename TEXT PRIMARY KEY,
                folder_id TEXT,
                FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE SET NULL
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("File system database initialized")
    
    def get_all_folders(self) -> List[Dict]:
        """Get all folders."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name, parent_id FROM folders")
        folders = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return folders
    
    def create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """Create a new folder."""
        folder_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO folders (id, name, parent_id) VALUES (?, ?, ?)",
            (folder_id, name, parent_id)
        )
        
        conn.commit()
        conn.close()
        logger.info(f"Created folder: {name} (ID: {folder_id})")
        return folder_id
    
    def update_folder(self, folder_id: str, name: Optional[str] = None, parent_id: Optional[str] = None):
        """Update a folder's name or parent."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
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
            cursor.execute(query, params)
            conn.commit()
        
        conn.close()
        logger.info(f"Updated folder ID: {folder_id}")
    
    def delete_folder(self, folder_id: str):
        """Delete a folder. Files in it become unsorted."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Remove file associations (files become unsorted)
        cursor.execute("DELETE FROM file_folders WHERE folder_id = ?", (folder_id,))
        
        # Delete the folder
        cursor.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
        
        conn.commit()
        conn.close()
        logger.info(f"Deleted folder ID: {folder_id}")
    
    def move_file_to_folder(self, filename: str, folder_id: Optional[str]):
        """Assign a file to a folder. folder_id='unsorted' removes mapping. None=Root."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if folder_id == 'unsorted':
            # Moving to unsorted: DELETE the entry entirely
            cursor.execute("DELETE FROM file_folders WHERE filename = ?", (filename,))
            logger.info(f"Moved file {filename} to unsorted (removed from file_folders)")
        else:
            # Moving to a folder (or Root if None): INSERT or UPDATE
            # Check if file already has a mapping
            cursor.execute("SELECT filename FROM file_folders WHERE filename = ?", (filename,))
            exists = cursor.fetchone()
            
            if exists:
                cursor.execute(
                    "UPDATE file_folders SET folder_id = ? WHERE filename = ?",
                    (folder_id, filename)
                )
            else:
                cursor.execute(
                    "INSERT INTO file_folders (filename, folder_id) VALUES (?, ?)",
                    (filename, folder_id)
                )
            logger.info(f"Moved file {filename} to folder {folder_id}")
        
        conn.commit()
        conn.close()
    
    def get_files_in_folders(self) -> Dict[str, List[str]]:
        """Get a mapping of folder_id -> [filenames]."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT filename, folder_id FROM file_folders")
        rows = cursor.fetchall()
        
        conn.close()
        
        # Build mapping
        result = {}
        for filename, folder_id in rows:
            # Use "null" string for None folder_id to match frontend expectations
            key = str(folder_id) if folder_id is not None else "null"
            if key not in result:
                result[key] = []
            result[key].append(filename)
        
        return result
    
    def get_unsorted_files(self, all_filenames: List[str]) -> List[str]:
        """
        Get files that are not assigned to any folder.
        all_filenames: List of all document filenames from the vector DB.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all files that have folder assignments
        cursor.execute("SELECT filename FROM file_folders")
        sorted_files = {row[0] for row in cursor.fetchall()}
        
        conn.close()
        
        # Return files that are not in the sorted set
        unsorted = [f for f in all_filenames if f not in sorted_files]
        return unsorted
    
    def remove_file(self, filename: str):
        """Remove a file from the file system (called when document is deleted)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM file_folders WHERE filename = ?", (filename,))
        
        conn.commit()
        conn.close()
        logger.info(f"Removed file {filename} from file system")

    def get_or_create_folder_path(self, path_components: List[str]) -> str:
        """
        Get or create a folder path from a list of folder names.
        
        Args:
            path_components: List of folder names in order, e.g., ['schoolwork', 'senior year', 'math']
        
        Returns:
            The ID of the final folder in the path
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        current_parent_id = None  # Start at root
        
        for folder_name in path_components:
            # Check if folder exists under current parent
            if current_parent_id is None:
                cursor.execute(
                    "SELECT id FROM folders WHERE name = ? AND parent_id IS NULL",
                    (folder_name,)
                )
            else:
                cursor.execute(
                    "SELECT id FROM folders WHERE name = ? AND parent_id = ?",
                    (folder_name, current_parent_id)
                )
            
            result = cursor.fetchone()
            
            if result:
                # Folder exists, use it
                current_parent_id = result['id']
                logger.info(f"Found existing folder: {folder_name} (ID: {current_parent_id})")
            else:
                # Folder doesn't exist, create it
                folder_id = str(uuid.uuid4())
                cursor.execute(
                    "INSERT INTO folders (id, name, parent_id) VALUES (?, ?, ?)",
                    (folder_id, folder_name, current_parent_id)
                )
                conn.commit()
                current_parent_id = folder_id
                logger.info(f"Created folder: {folder_name} (ID: {folder_id}, Parent: {current_parent_id})")
        
        conn.close()
        return current_parent_id

    def reset_db(self):
        """Reset the database by clearing all tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM file_folders")
        cursor.execute("DELETE FROM folders")
        
        conn.commit()
        conn.close()
        logger.info("File system database reset")


# Global instance
fs_db = FileSystemDB()
