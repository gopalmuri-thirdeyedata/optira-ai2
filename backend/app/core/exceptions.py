"""
Custom exceptions for the application.
"""
from typing import Any


class BaseAppException(Exception):
    """Base exception for application errors."""
    
    def __init__(self, message: str, details: Any = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class UnsupportedFileTypeError(BaseAppException):
    """Raised when file type is not supported."""
    pass


class FileTooLargeError(BaseAppException):
    """Raised when file exceeds size limit."""
    pass


class ParsingError(BaseAppException):
    """Raised when file parsing fails."""
    pass


class TemplateAnalysisError(BaseAppException):
    """Raised when template analysis fails."""
    pass


class PlaceholderNotFoundError(BaseAppException):
    """Raised when no placeholders are found in template."""
    pass


class AIMapperError(BaseAppException):
    """Raised when AI mapping fails."""
    pass


class AIResponseValidationError(BaseAppException):
    """Raised when AI response fails validation."""
    pass


class RenderingError(BaseAppException):
    """Raised when content replacement/rendering fails."""
    pass


class GroqAPIError(BaseAppException):
    """Raised when Groq API call fails."""
    pass


class AnalysisError(BaseAppException):
    """Raised when document analysis fails."""
    pass

