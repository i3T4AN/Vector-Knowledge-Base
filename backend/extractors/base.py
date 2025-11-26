# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         Base extractor interface
# =======================================================================

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple

class BaseExtractor(ABC):
    """Base class for all file extractors"""
    
    @abstractmethod
    def extract(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Extract text and metadata from a file.
        
        Args:
            file_path: Path to the file to extract from
            
        Returns:
            Tuple containing:
            - Extracted text content
            - Metadata dictionary (e.g., page count, author)
        """
        pass
