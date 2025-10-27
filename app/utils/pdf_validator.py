# app/utils/pdf_validator.py
"""
PDF validation utilities for file size, page count, and content validation.
"""

import io
import logging
from typing import Tuple, Optional
import PyPDF2
from .pdf_exceptions import (
    LargeFileError, 
    TooManyPagesError, 
    CorruptedPDFError,
    PasswordProtectedPDFError,
    EmptyPDFError,
    InvalidMimeTypeError
)

logger = logging.getLogger(__name__)

class PDFValidator:
    """Validates PDF files for various constraints and issues"""
    
    def __init__(self, max_file_size: int = 50 * 1024 * 1024, max_pages: int = 1000):
        """
        Initialize PDF validator with constraints
        
        Args:
            max_file_size: Maximum file size in bytes (default: 50MB)
            max_pages: Maximum number of pages allowed (default: 1000)
        """
        self.max_file_size = max_file_size
        self.max_pages = max_pages
    
    def validate_file_size(self, file_size: int) -> None:
        """Validate file size is within limits"""
        if file_size > self.max_file_size:
            raise LargeFileError(file_size, self.max_file_size)
    
    def validate_mime_type(self, file_content: bytes, filename: str = None) -> None:
        """Validate that the file is actually a PDF"""
        # Check PDF header signature
        if not file_content.startswith(b"%PDF-"):
            detected_type = "unknown"
            try:
                import magic
                ms = magic.Magic(mime=True)
                detected_type = ms.from_buffer(file_content[:1024])
            except ImportError:
                logger.warning("python-magic not available for MIME type detection")
            except Exception as e:
                logger.warning(f"MIME type detection failed: {e}")
            
            raise InvalidMimeTypeError(detected_type)
    
    def validate_pdf_structure(self, pdf_content: bytes) -> Tuple[int, bool, bool]:
        """
        Validate PDF structure and extract basic information
        
        Returns:
            Tuple of (page_count, is_password_protected, is_readable)
        """
        try:
            pdf_file = io.BytesIO(pdf_content)
            reader = PyPDF2.PdfReader(pdf_file)
            
            # Check if PDF is encrypted/password protected
            is_password_protected = reader.is_encrypted
            
            # Get page count
            page_count = len(reader.pages)
            
            # Validate page count
            if page_count > self.max_pages:
                raise TooManyPagesError(page_count, self.max_pages)
            
            # Try to read first page to check if content is readable
            is_readable = False
            if page_count > 0:
                try:
                    first_page = reader.pages[0]
                    text = first_page.extract_text()
                    is_readable = bool(text and text.strip())
                except Exception as e:
                    logger.warning(f"Could not extract text from first page: {e}")
            
            return page_count, is_password_protected, is_readable
            
        except PyPDF2.errors.PdfReadError as e:
            logger.error(f"PDF read error: {e}")
            raise CorruptedPDFError(f"PDF file is corrupted or malformed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error validating PDF: {e}")
            raise CorruptedPDFError(f"Error validating PDF structure: {str(e)}")
    
    def validate_content_readability(self, pdf_content: bytes) -> Tuple[int, int]:
        """
        Validate PDF content readability and return readable vs total pages
        
        Returns:
            Tuple of (readable_pages, total_pages)
        """
        try:
            pdf_file = io.BytesIO(pdf_content)
            reader = PyPDF2.PdfReader(pdf_file)
            
            if reader.is_encrypted:
                raise PasswordProtectedPDFError()
            
            total_pages = len(reader.pages)
            readable_pages = 0
            
            for i, page in enumerate(reader.pages):
                try:
                    text = page.extract_text()
                    if text and text.strip():
                        readable_pages += 1
                except Exception as e:
                    logger.warning(f"Could not extract text from page {i+1}: {e}")
            
            if readable_pages == 0:
                raise EmptyPDFError()
            
            return readable_pages, total_pages
            
        except PasswordProtectedPDFError:
            raise
        except EmptyPDFError:
            raise
        except Exception as e:
            logger.error(f"Error validating content readability: {e}")
            raise CorruptedPDFError(f"Error validating PDF content: {str(e)}")
    
    def comprehensive_validation(self, pdf_content: bytes, file_size: int, filename: str = None) -> dict:
        """
        Perform comprehensive PDF validation
        
        Returns:
            Dictionary with validation results
        """
        logger.info(f"Starting comprehensive PDF validation for file: {filename}")
        
        # File size validation
        self.validate_file_size(file_size)
        logger.info(f"File size validation passed: {file_size} bytes")
        
        # MIME type validation
        self.validate_mime_type(pdf_content, filename)
        logger.info("MIME type validation passed")
        
        # PDF structure validation
        page_count, is_password_protected, is_readable = self.validate_pdf_structure(pdf_content)
        logger.info(f"PDF structure validation passed: {page_count} pages, encrypted: {is_password_protected}")
        
        if is_password_protected:
            raise PasswordProtectedPDFError()
        
        # Content readability validation
        readable_pages, total_pages = self.validate_content_readability(pdf_content)
        logger.info(f"Content validation passed: {readable_pages}/{total_pages} pages readable")
        
        return {
            "file_size": file_size,
            "total_pages": total_pages,
            "readable_pages": readable_pages,
            "is_password_protected": is_password_protected,
            "is_readable": is_readable,
            "validation_passed": True
        }
