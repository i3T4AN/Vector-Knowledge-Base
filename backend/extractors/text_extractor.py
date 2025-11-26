# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         Plain text file extractor
# =======================================================================

from typing import Tuple, Dict, Any
import logging
from .base import BaseExtractor

logger = logging.getLogger(__name__)

class TextExtractor(BaseExtractor):
    def extract(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                text = file.read()
            
            metadata = {"encoding": "utf-8"}
            return text, metadata
            
        except Exception as e:
            logger.error(f"Error extracting Text file {file_path}: {str(e)}")
            raise ValueError(f"Failed to extract Text file: {str(e)}")
