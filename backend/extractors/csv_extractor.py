# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         CSV file text extractor
# =======================================================================

import csv
import io
import os
from typing import Dict, Any, Tuple, Optional
from .base import BaseExtractor
from exceptions import ExtractionError

class CsvExtractor(BaseExtractor):
    """Extractor for CSV (.csv) files."""

    def extract(self, file_path: str, file_content: Optional[bytes] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Extract text content and metadata from a CSV file.
        
        Args:
            file_path: Path to the file
            file_content: Optional binary content of the file
            
        Returns:
            Tuple containing (extracted_text, metadata)
        """
        try:
            # Determine content to read
            if file_content:
                content_bytes = file_content
            else:
                with open(file_path, 'rb') as f:
                    content_bytes = f.read()
            
            # Try to detect encoding
            encoding = 'utf-8'
            try:
                content_str = content_bytes.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    content_str = content_bytes.decode('latin-1')
                    encoding = 'latin-1'
                except UnicodeDecodeError:
                    content_str = content_bytes.decode('cp1252', errors='replace')
                    encoding = 'cp1252'
            
            # Use Sniffer to detect delimiter
            try:
                # Sample first 4KB for sniffing
                sample = content_str[:4096]
                dialect = csv.Sniffer().sniff(sample)
                has_header = csv.Sniffer().has_header(sample)
                delimiter = dialect.delimiter
            except csv.Error:
                # Fallback defaults
                delimiter = ','
                has_header = False
                
            # Parse CSV
            f = io.StringIO(content_str)
            reader = csv.reader(f, delimiter=delimiter)
            
            rows = []
            row_count = 0
            col_count = 0
            
            for row in reader:
                if not row:
                    continue
                    
                row_count += 1
                col_count = max(col_count, len(row))
                
                # Format row: "Col1 | Col2 | Col3"
                # Filter out empty strings if desired, or keep them to preserve structure
                # Here we keep them but strip whitespace
                clean_row = [cell.strip() for cell in row]
                rows.append(" | ".join(clean_row))
            
            metadata = {
                "row_count": row_count,
                "column_count": col_count,
                "has_header": has_header,
                "delimiter": delimiter,
                "encoding": encoding,
                "file_size": len(content_bytes)
            }
            
            return "\n".join(rows), metadata
            
        except Exception as e:
            raise ExtractionError(f"Error extracting text from CSV file: {str(e)}")
