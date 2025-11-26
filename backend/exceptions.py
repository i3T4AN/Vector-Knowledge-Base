# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         Custom exception definitions
# =======================================================================

class VectorDBException(Exception):
    """Base exception for the application."""
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)

class InvalidFileFormatError(VectorDBException):
    """Raised when the uploaded file format is not supported."""
    pass

class FileSizeExceededError(VectorDBException):
    """Raised when the file size exceeds the allowed limit."""
    pass

class ExtractionError(VectorDBException):
    """Raised when text extraction fails."""
    pass

class EmbeddingError(VectorDBException):
    """Raised when embedding generation fails."""
    pass

class VectorDBError(VectorDBException):
    """Raised when an operation on the vector database fails."""
    pass
