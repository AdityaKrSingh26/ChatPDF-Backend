# app/utils/pdf_processor.py
from typing import List, Tuple, Optional
import PyPDF2
import io
import numpy as np
import logging
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from ..config import settings
from .pdf_exceptions import (
    PDFProcessingError, 
    CorruptedPDFError, 
    PasswordProtectedPDFError,
    EmptyPDFError,
    PartialReadError
)
from .pdf_validator import PDFValidator
from .retry_handler import RetryHandler, retry_on_failure
from .timeout_handler import TimeoutHandler, with_timeout

logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self, max_file_size: int = 50 * 1024 * 1024, max_pages: int = 1000):
        # Initialize sentence-transformers model for embeddings
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        # Initialize Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')
        self.chunk_size = 1000
        self.chunk_overlap = 200
        
        # Initialize validators and handlers
        self.validator = PDFValidator(max_file_size, max_pages)
        self.retry_handler = RetryHandler(max_retries=3, base_delay=1.0)
        self.timeout_handler = TimeoutHandler(timeout_seconds=300)
        
    @retry_on_failure(max_retries=3, base_delay=1.0)
    @with_timeout(timeout_seconds=300)
    async def extract_text_from_pdf(self, pdf_content: bytes, filename: str = None) -> Tuple[str, dict]:
        """
        Extract text content from PDF bytes with comprehensive error handling
        
        Returns:
            Tuple of (extracted_text, processing_info)
        """
        logger.info(f"Starting PDF text extraction for file: {filename}")
        
        try:
            # Validate PDF before processing
            file_size = len(pdf_content)
            validation_result = self.validator.comprehensive_validation(
                pdf_content, file_size, filename
            )
            logger.info(f"PDF validation passed: {validation_result}")
            
            pdf_file = io.BytesIO(pdf_content)
            reader = PyPDF2.PdfReader(pdf_file)
            
            # Check for password protection
            if reader.is_encrypted:
                logger.error("PDF is password protected")
                raise PasswordProtectedPDFError()
            
            text = ""
            readable_pages = 0
            total_pages = len(reader.pages)
            
            logger.info(f"Processing {total_pages} pages")
            
            for i, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text += page_text + "\n"
                        readable_pages += 1
                    logger.debug(f"Page {i+1} processed successfully")
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {i+1}: {str(e)}")
                    continue
            
            if not text.strip():
                logger.error("No readable text found in PDF")
                raise EmptyPDFError()
            
            # Check for partial readability
            if readable_pages < total_pages:
                logger.warning(f"Only {readable_pages}/{total_pages} pages were readable")
                if readable_pages < total_pages * 0.5:  # Less than 50% readable
                    raise PartialReadError(readable_pages, total_pages)
            
            processing_info = {
                "total_pages": total_pages,
                "readable_pages": readable_pages,
                "text_length": len(text),
                "validation_passed": True,
                "partial_read": readable_pages < total_pages
            }
            
            logger.info(f"PDF text extraction completed: {readable_pages}/{total_pages} pages, {len(text)} characters")
            return text.strip(), processing_info
            
        except (PasswordProtectedPDFError, EmptyPDFError, PartialReadError):
            raise
        except PyPDF2.errors.PdfReadError as e:
            logger.error(f"PDF read error: {str(e)}")
            raise CorruptedPDFError(f"PDF file is corrupted or malformed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during PDF text extraction: {str(e)}")
            raise PDFProcessingError(f"Error extracting text from PDF: {str(e)}")

    def create_chunks(self, text: str) -> List[str]:
        """Split text into chunks with overlap"""
        logger.info(f"Creating chunks from text of length {len(text)}")
        
        try:
            words = text.split()
            chunks = []
            
            for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
                chunk = " ".join(words[i:i + self.chunk_size])
                chunks.append(chunk)
            
            logger.info(f"Created {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Error creating chunks: {str(e)}")
            raise PDFProcessingError(f"Error creating text chunks: {str(e)}")

    @retry_on_failure(max_retries=2, base_delay=1.0)
    async def get_embeddings(self, text: str) -> List[float]:
        """Get embeddings using sentence-transformers"""
        logger.debug(f"Getting embeddings for text of length {len(text)}")
        
        try:
            embedding = self.embedding_model.encode(text)
            logger.debug("Embeddings generated successfully")
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error getting embeddings: {str(e)}")
            raise PDFProcessingError(f"Error getting embeddings: {str(e)}")

    @retry_on_failure(max_retries=2, base_delay=1.0)
    async def find_relevant_chunks(self, query: str, chunks: List[str], top_k: int = 3) -> List[str]:
        """Find most relevant chunks for the query using cosine similarity"""
        logger.info(f"Finding relevant chunks for query: '{query[:50]}...' from {len(chunks)} chunks")
        
        try:
            if not chunks:
                logger.warning("No chunks provided for similarity search")
                return []
            
            # Get query embedding
            query_embedding = await self.get_embeddings(query)
            
            # Get embeddings for all chunks
            chunk_embeddings = []
            for i, chunk in enumerate(chunks):
                try:
                    embedding = await self.get_embeddings(chunk)
                    chunk_embeddings.append(embedding)
                    logger.debug(f"Generated embedding for chunk {i+1}")
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for chunk {i+1}: {str(e)}")
                    continue
            
            if not chunk_embeddings:
                logger.error("No embeddings could be generated for chunks")
                raise PDFProcessingError("Failed to generate embeddings for any chunks")
            
            # Calculate cosine similarity
            similarities = [
                cosine_similarity(
                    [query_embedding],
                    [chunk_embedding]
                )[0][0]
                for chunk_embedding in chunk_embeddings
            ]
            
            # Get top k chunks
            top_indices = np.argsort(similarities)[-top_k:]
            relevant_chunks = [chunks[i] for i in top_indices if i < len(chunks)]
            
            logger.info(f"Found {len(relevant_chunks)} relevant chunks")
            return relevant_chunks
            
        except Exception as e:
            logger.error(f"Error finding relevant chunks: {str(e)}")
            raise PDFProcessingError(f"Error finding relevant chunks: {str(e)}")

    @retry_on_failure(max_retries=2, base_delay=2.0)
    @with_timeout(timeout_seconds=60)
    async def generate_response(self, query: str, relevant_chunks: List[str]) -> str:
        """Generate response using Gemini Pro"""
        logger.info(f"Generating response for query: '{query[:50]}...' using {len(relevant_chunks)} chunks")
        
        try:
            if not relevant_chunks:
                logger.warning("No relevant chunks provided for response generation")
                return "I cannot answer this question as no relevant content was found in the PDF."
            
            # Combine relevant chunks
            context = "\n".join(relevant_chunks)
            logger.debug(f"Combined context length: {len(context)} characters")
            
            # Create prompt
            prompt = f"""You are a helpful assistant that answers questions based on provided PDF content.
            
Context from PDF:
{context}

Question: {query}

Instructions:
1. Answer based ONLY on the provided context
2. If the answer isn't in the context, say "I cannot answer this based on the provided content"
3. Be concise but thorough
4. If relevant, cite specific parts of the context
5. If the PDF appears to have partial content or scanning issues, mention this limitation

Answer:"""
            
            # Generate response using Gemini
            logger.debug("Sending request to Gemini API")
            response = self.model.generate_content(prompt)
            
            if not response.text:
                logger.warning("Empty response received from Gemini")
                return "I apologize, but I was unable to generate a response. Please try rephrasing your question."
            
            logger.info("Response generated successfully")
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise PDFProcessingError(f"Error generating response: {str(e)}")

    async def process_pdf_with_fallback(self, pdf_content: bytes, filename: str = None) -> Tuple[str, dict]:
        """
        Process PDF with graceful degradation for partially readable content
        
        Returns:
            Tuple of (extracted_text, processing_info)
        """
        logger.info(f"Starting PDF processing with fallback for file: {filename}")
        
        try:
            # Try normal processing first
            text, processing_info = await self.extract_text_from_pdf(pdf_content, filename)
            return text, processing_info
            
        except PartialReadError as e:
            logger.warning(f"Partial read detected: {str(e)}")
            # Try to extract what we can
            try:
                pdf_file = io.BytesIO(pdf_content)
                reader = PyPDF2.PdfReader(pdf_file)
                
                text = ""
                readable_pages = 0
                total_pages = len(reader.pages)
                
                for i, page in enumerate(reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text and page_text.strip():
                            text += page_text + "\n"
                            readable_pages += 1
                    except Exception:
                        continue
                
                if text.strip():
                    processing_info = {
                        "total_pages": total_pages,
                        "readable_pages": readable_pages,
                        "text_length": len(text),
                        "validation_passed": True,
                        "partial_read": True,
                        "fallback_used": True
                    }
                    
                    logger.info(f"Fallback processing successful: {readable_pages}/{total_pages} pages")
                    return text.strip(), processing_info
                else:
                    raise EmptyPDFError()
                    
            except Exception as fallback_error:
                logger.error(f"Fallback processing also failed: {str(fallback_error)}")
                raise EmptyPDFError()
        
        except Exception as e:
            logger.error(f"PDF processing failed: {str(e)}")
            raise

pdf_processor = PDFProcessor()