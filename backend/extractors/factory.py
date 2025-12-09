# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         Extractor factory pattern
# =======================================================================

import os
from typing import Dict, Type
from .base import BaseExtractor
from .pdf_extractor import PDFExtractor
from .docx_extractor import DocxExtractor
from .pptx_extractor import PptxExtractor
from .image_extractor import ImageExtractor
from .text_extractor import TextExtractor
from .code_extractor import CodeExtractor
from .cs_extractor import CsExtractor
from .xlsx_extractor import XlsxExtractor
from .csv_extractor import CsvExtractor
from exceptions import InvalidFileFormatError

class ExtractorFactory:
    _extractors: Dict[str, Type[BaseExtractor]] = {
        '.pdf': PDFExtractor,
        '.docx': DocxExtractor,
        '.pptx': PptxExtractor,
        '.ppt': PptxExtractor,
        '.jpg': ImageExtractor,
        '.jpeg': ImageExtractor,
        '.png': ImageExtractor,
        '.webp': ImageExtractor,
        '.txt': TextExtractor,
        '.md': TextExtractor,
        '.py': CodeExtractor,
        '.js': CodeExtractor,
        '.java': CodeExtractor,
        '.cpp': CodeExtractor,
        '.html': CodeExtractor,
        '.css': CodeExtractor,
        '.json': CodeExtractor,
        '.xml': CodeExtractor,
        '.yaml': CodeExtractor,
        '.yml': CodeExtractor,
        '.cs': CsExtractor,
        '.xlsx': XlsxExtractor,
        '.csv': CsvExtractor
    }

    @classmethod
    def get_extractor(cls, file_path: str) -> BaseExtractor:
        """
        Get the appropriate extractor for the given file path.
        
        Args:
            file_path: Path to the file
            
        Returns:
            An instance of the appropriate extractor
            
        Raises:
            InvalidFileFormatError: If the file extension is not supported
        """
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        extractor_class = cls._extractors.get(ext)
        
        if not extractor_class:
            raise InvalidFileFormatError(f"Unsupported file extension: {ext}")
            
        return extractor_class()

