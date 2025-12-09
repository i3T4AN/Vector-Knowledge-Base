# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         DOCX document text extractor
# =======================================================================

from typing import Tuple, Dict, Any
import docx2txt
import logging
from .base import BaseExtractor
from exceptions import ExtractionError

logger = logging.getLogger(__name__)

class DocxExtractor(BaseExtractor):
    def extract(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        try:
            # docx2txt extracts text directly
            text = docx2txt.process(file_path)
            metadata = {} # DOCX metadata extraction is limited with docx2txt
            
            return text, metadata
            
        except Exception as e:
            logger.error(f"Error extracting DOCX {file_path}: {str(e)}")
            raise ExtractionError(f"Failed to extract DOCX: {str(e)}")

