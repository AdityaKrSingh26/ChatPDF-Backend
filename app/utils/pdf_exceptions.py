# app/utils/pdf_exceptions.py
"""
Custom exceptions for PDF processing with specific error types and messages.
"""

class PDFProcessingError(Exception):
    """Base exception for PDF processing errors"""
    def __init__(self, message: str, error_code: str = "PDF_PROCESSING_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class CorruptedPDFError(PDFProcessingError):
    """Raised when PDF file is corrupted or malformed"""
    def __init__(self, message: str = "The PDF file appears to be corrupted or malformed"):
        super().__init__(message, "CORRUPTED_PDF")

class PasswordProtectedPDFError(PDFProcessingError):
    """Raised when PDF is password protected"""
    def __init__(self, message: str = "The PDF file is password protected and cannot be processed"):
        super().__init__(message, "PASSWORD_PROTECTED_PDF")

class EmptyPDFError(PDFProcessingError):
    """Raised when PDF has no readable content"""
    def __init__(self, message: str = "The PDF file contains no readable text content"):
        super().__init__(message, "EMPTY_PDF")

class LargeFileError(PDFProcessingError):
    """Raised when PDF file is too large"""
    def __init__(self, file_size: int, max_size: int):
        message = f"PDF file size ({file_size} bytes) exceeds maximum allowed size ({max_size} bytes)"
        super().__init__(message, "FILE_TOO_LARGE")

class TooManyPagesError(PDFProcessingError):
    """Raised when PDF has too many pages"""
    def __init__(self, page_count: int, max_pages: int):
        message = f"PDF has {page_count} pages, which exceeds maximum allowed pages ({max_pages})"
        super().__init__(message, "TOO_MANY_PAGES")

class ProcessingTimeoutError(PDFProcessingError):
    """Raised when PDF processing times out"""
    def __init__(self, timeout_seconds: int):
        message = f"PDF processing timed out after {timeout_seconds} seconds"
        super().__init__(message, "PROCESSING_TIMEOUT")

class InvalidMimeTypeError(PDFProcessingError):
    """Raised when file is not a valid PDF"""
    def __init__(self, detected_mime: str = None):
        message = f"Invalid file type. Expected PDF, got: {detected_mime or 'unknown'}"
        super().__init__(message, "INVALID_MIME_TYPE")

class PartialReadError(PDFProcessingError):
    """Raised when PDF can only be partially read"""
    def __init__(self, readable_pages: int, total_pages: int):
        message = f"Only {readable_pages} out of {total_pages} pages could be processed"
        super().__init__(message, "PARTIAL_READ")

class RetryExhaustedError(PDFProcessingError):
    """Raised when all retry attempts are exhausted"""
    def __init__(self, max_retries: int):
        message = f"PDF processing failed after {max_retries} retry attempts"
        super().__init__(message, "RETRY_EXHAUSTED")
