# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         Image OCR text extractor
# =======================================================================

from typing import Tuple, Dict, Any
from PIL import Image
import pytesseract
import logging
import os
from .base import BaseExtractor
from exceptions import ExtractionError

# Configure logging
logger = logging.getLogger(__name__)

class ImageExtractor(BaseExtractor):
    def extract(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Extract text from image using OCR.
        
        Features:
        - Automatic image preprocessing (grayscale)
        - Multi-language support (default: English)
        - Image dimension metadata
        """
        try:
            # Open the image file
            with Image.open(file_path) as img:
                # Get image metadata
                width, height = img.size
                format = img.format
                mode = img.mode
                
                # Convert to grayscale for better OCR accuracy
                # This is a basic preprocessing step
                gray_img = img.convert('L')
                
                # Extract text using pytesseract
                # timeout=10 to prevent hanging on very large/complex images
                text = pytesseract.image_to_string(gray_img, timeout=10)
                
                # Clean up the text
                text = text.strip()
                
                # Prepare metadata
                metadata = {
                    "width": width,
                    "height": height,
                    "format": format,
                    "mode": mode,
                    "file_size": os.path.getsize(file_path),
                    "ocr_engine": "tesseract"
                }
                
                if not text:
                    logger.warning(f"No text extracted from image: {file_path}")
                    return "", metadata
                
                return text, metadata
                
        except pytesseract.TesseractError as e:
            logger.error(f"Tesseract OCR error for {file_path}: {str(e)}")
            raise ExtractionError(f"Failed to extract text from image: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing image {file_path}: {str(e)}")
            raise ExtractionError(f"Error processing image: {str(e)}")
