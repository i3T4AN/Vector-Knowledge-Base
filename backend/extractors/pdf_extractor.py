# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         PDF document text extractor
# =======================================================================

from typing import Tuple, Dict, Any
import pypdf
import logging
from .base import BaseExtractor

logger = logging.getLogger(__name__)

class PDFExtractor(BaseExtractor):
    def extract(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        try:
            text_content = []
            metadata = {"page_count": 0}
            
            with open(file_path, 'rb') as file:
                reader = pypdf.PdfReader(file)
                metadata["page_count"] = len(reader.pages)
                
                # Extract metadata if available
                if reader.metadata:
                    if reader.metadata.author:
                        metadata["author"] = reader.metadata.author
                    if reader.metadata.title:
                        metadata["title"] = reader.metadata.title
                
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text:
                        text_content.append(text)
            
            return "\n\n".join(text_content), metadata
            
        except Exception as e:
            logger.error(f"Error extracting PDF {file_path}: {str(e)}")
            raise ValueError(f"Failed to extract PDF: {str(e)}")
