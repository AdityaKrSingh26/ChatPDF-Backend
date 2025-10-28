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

logger = logging.getLogger(__name__)

# Minimal custom exceptions (inlined to keep implementation small and self-contained)
class PDFProcessingError(Exception):
    pass

class CorruptedPDFError(PDFProcessingError):
    pass

class PasswordProtectedPDFError(PDFProcessingError):
    pass

class EmptyPDFError(PDFProcessingError):
    pass

class PartialReadError(PDFProcessingError):
    def __init__(self, readable_pages: int, total_pages: int):
        super().__init__(f"Only {readable_pages}/{total_pages} pages readable")
        self.readable_pages = readable_pages
        self.total_pages = total_pages

class PDFProcessor:
    def __init__(self, max_file_size: int = 50 * 1024 * 1024, max_pages: int = 1000):
        # Initialize sentence-transformers model for embeddings
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        # Initialize Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')
        self.chunk_size = 1000
        self.chunk_overlap = 200
        self.max_file_size = max_file_size
        self.max_pages = max_pages

    def quick_validate(self, pdf_content: bytes, filename: str = None) -> None:
        """Minimal validation: size, header, structure, encryption, page count."""
        size = len(pdf_content)
        if size == 0 or size > self.max_file_size:
            raise PDFProcessingError("File size invalid or too large (limit 50MB)")
        if not pdf_content.startswith(b"%PDF-"):
            raise PDFProcessingError("Invalid file type. Expected a PDF")
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
        except PyPDF2.errors.PdfReadError as e:
            raise CorruptedPDFError(str(e))
        except Exception as e:
            raise CorruptedPDFError(str(e))
        if getattr(reader, "is_encrypted", False):
            raise PasswordProtectedPDFError("PDF is password protected")
        if len(reader.pages) > self.max_pages:
            raise PDFProcessingError("PDF has too many pages")

    async def extract_text_from_pdf(self, pdf_content: bytes, filename: str = None) -> Tuple[str, dict]:
        """Extract text with minimal, robust handling."""
        try:
            self.quick_validate(pdf_content, filename)
            
            pdf_file = io.BytesIO(pdf_content)
            reader = PyPDF2.PdfReader(pdf_file)
            
            if reader.is_encrypted:
                raise PasswordProtectedPDFError()
            
            text = ""
            readable_pages = 0
            total_pages = len(reader.pages)
            
            for i, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text += page_text + "\n"
                        readable_pages += 1
                except Exception as e:
                    continue
            
            if not text.strip():
                raise EmptyPDFError()
            
            if readable_pages < total_pages:
                if readable_pages < total_pages * 0.5:  # Less than 50% readable
                    raise PartialReadError(readable_pages, total_pages)
            
            processing_info = {
                "total_pages": total_pages,
                "readable_pages": readable_pages,
                "text_length": len(text),
                "partial_read": readable_pages < total_pages
            }
            
            return text.strip(), processing_info
            
        except (PasswordProtectedPDFError, EmptyPDFError, PartialReadError):
            raise
        except PyPDF2.errors.PdfReadError as e:
            raise CorruptedPDFError(f"PDF file is corrupted or malformed: {str(e)}")
        except Exception as e:
            raise PDFProcessingError(f"Error extracting text from PDF: {str(e)}")

    def create_chunks(self, text: str) -> List[str]:
        """Split text into chunks with overlap"""
        try:
            words = text.split()
            chunks = []
            
            for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
                chunk = " ".join(words[i:i + self.chunk_size])
                chunks.append(chunk)
            
            return chunks
            
        except Exception as e:
            raise PDFProcessingError(f"Error creating text chunks: {str(e)}")

    async def get_embeddings(self, text: str) -> List[float]:
        """Get embeddings using sentence-transformers"""
        try:
            embedding = self.embedding_model.encode(text)
            return embedding.tolist()
        except Exception as e:
            raise PDFProcessingError(f"Error getting embeddings: {str(e)}")

    async def find_relevant_chunks(self, query: str, chunks: List[str], top_k: int = 3) -> List[str]:
        """Find most relevant chunks for the query using cosine similarity"""
        try:
            if not chunks:
                return []
            
            # Get query embedding
            query_embedding = await self.get_embeddings(query)
            
            # Get embeddings for all chunks
            chunk_embeddings = []
            for i, chunk in enumerate(chunks):
                try:
                    embedding = await self.get_embeddings(chunk)
                    chunk_embeddings.append(embedding)
                except Exception as e:
                    continue
            
            if not chunk_embeddings:
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
            
            return relevant_chunks
            
        except Exception as e:
            raise PDFProcessingError(f"Error finding relevant chunks: {str(e)}")

    async def generate_response(self, query: str, relevant_chunks: List[str]) -> str:
        """Generate response using Gemini Pro"""
        try:
            if not relevant_chunks:
                return "I cannot answer this question as no relevant content was found in the PDF."
            
            # Combine relevant chunks
            context = "\n".join(relevant_chunks)
            prompt = f"Answer using ONLY the context; otherwise say you don't know.\n\nContext:\n{context}\n\nQuestion: {query}\n\nAnswer:"
            
            response = self.model.generate_content(prompt)
            
            if not response.text:
                return "I apologize, but I was unable to generate a response. Please try rephrasing your question."
            return response.text
            
        except Exception as e:
            raise PDFProcessingError(f"Error generating response: {str(e)}")

    async def process_pdf_with_fallback(self, pdf_content: bytes, filename: str = None) -> Tuple[str, dict]:
        """Process PDF with graceful degradation for partially readable content"""
        
        try:
            text, processing_info = await self.extract_text_from_pdf(pdf_content, filename)
            return text, processing_info
            
        except PartialReadError as e:
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
                    
                    return text.strip(), processing_info
                else:
                    raise EmptyPDFError()
                    
            except Exception as fallback_error:
                raise EmptyPDFError()
        
        except Exception as e:
            raise

pdf_processor = PDFProcessor()