# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         C# file text extractor
# =======================================================================

from typing import Tuple, Dict, Any
import logging
import os
from .base import BaseExtractor
from exceptions import ExtractionError

logger = logging.getLogger(__name__)

class CsExtractor(BaseExtractor):
    def extract(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Extract text from C# source code files.
        
        Features:
        - Preserve code structure and formatting
        - Extract using UTF-8 encoding
        - Track file metadata (lines, size)
        """
        try:
            # Default to UTF-8, fallback to latin-1 if needed (though ignore covers most)
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                text = file.read()
            
            # Basic metadata
            file_stats = os.stat(file_path)
            line_count = len(text.splitlines())
            
            metadata = {
                "language": "cs",
                "file_size": file_stats.st_size,
                "line_count": line_count
            }
            
            # Optional: Try to detect namespace (simple heuristic)
            for line in text.splitlines()[:20]:  # Check first 20 lines
                if line.strip().startswith("namespace "):
                    metadata["namespace"] = line.strip().split()[1].rstrip(";")
                    break
            
            return text, metadata
            
        except Exception as e:
            logger.error(f"Error extracting C# file {file_path}: {str(e)}")
            raise ExtractionError(f"Failed to extract C# file: {str(e)}")
