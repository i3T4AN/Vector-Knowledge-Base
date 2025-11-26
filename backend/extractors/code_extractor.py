# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         Code file text extractor
# =======================================================================

from typing import Tuple, Dict, Any
import logging
from .base import BaseExtractor

logger = logging.getLogger(__name__)

class CodeExtractor(BaseExtractor):
    def extract(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                text = file.read()
            
            # Basic metadata for code
            import os
            extension = os.path.splitext(file_path)[1]
            metadata = {"language": extension.lstrip('.')}
            
            return text, metadata
            
        except Exception as e:
            logger.error(f"Error extracting Code file {file_path}: {str(e)}")
            raise ValueError(f"Failed to extract Code file: {str(e)}")
