# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         Extractor module initialization
# =======================================================================

# Extractors package
from .base import BaseExtractor
from .pdf_extractor import PDFExtractor
from .docx_extractor import DocxExtractor
from .text_extractor import TextExtractor
from .code_extractor import CodeExtractor
from .factory import ExtractorFactory
