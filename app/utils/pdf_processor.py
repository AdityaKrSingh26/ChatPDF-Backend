from typing import List, Tuple
import PyPDF2, io, numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from ..config import settings

# Minimal custom exceptions
class PDFProcessingError(Exception): pass
class CorruptedPDFError(PDFProcessingError): pass
class PasswordProtectedPDFError(PDFProcessingError): pass
class EmptyPDFError(PDFProcessingError): pass

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
        try:
            self.quick_validate(pdf_content, filename)
            
            pdf_file = io.BytesIO(pdf_content)
            reader = PyPDF2.PdfReader(pdf_file)
            
            if reader.is_encrypted:
                raise PasswordProtectedPDFError()
            
            text = ""; readable_pages = 0; total_pages = len(reader.pages)
            for page in reader.pages:
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text += page_text + "\n"
                        readable_pages += 1
                except Exception as e:
                    continue
            
            if not text.strip():
                raise EmptyPDFError()
            
            if readable_pages*2 < total_pages:
                raise PartialReadError(readable_pages, total_pages)
            
            info = {"total_pages": total_pages, "readable_pages": readable_pages, "text_length": len(text), "partial_read": readable_pages < total_pages}
            return text.strip(), info
            
        except (PasswordProtectedPDFError, EmptyPDFError, PartialReadError):
            raise
        except PyPDF2.errors.PdfReadError as e:
            raise CorruptedPDFError(f"PDF file is corrupted or malformed: {str(e)}")
        except Exception as e:
            raise PDFProcessingError(f"Error extracting text from PDF: {str(e)}")

    def create_chunks(self, text: str) -> List[str]:
        try:
            words = text.split(); step = self.chunk_size - self.chunk_overlap
            return [" ".join(words[i:i + self.chunk_size]) for i in range(0, len(words), step)]
        except Exception as e:
            raise PDFProcessingError(f"Error creating text chunks: {str(e)}")

    async def get_embeddings(self, text: str) -> List[float]:
        try:
            embedding = self.embedding_model.encode(text)
            return embedding.tolist()
        except Exception as e:
            raise PDFProcessingError(f"Error getting embeddings: {str(e)}")

    async def find_relevant_chunks(self, query: str, chunks: List[str], top_k: int = 3) -> List[str]:
        try:
            if not chunks: return []
            q = await self.get_embeddings(query)
            embs = []
            for c in chunks:
                try: embs.append(await self.get_embeddings(c))
                except Exception: continue
            if not embs: raise PDFProcessingError("Failed to generate embeddings for any chunks")
            sims = [cosine_similarity([q],[e])[0][0] for e in embs]
            idx = np.argsort(sims)[-top_k:]
            return [chunks[i] for i in idx if i < len(chunks)]
        except Exception as e:
            raise PDFProcessingError(f"Error finding relevant chunks: {str(e)}")

    async def generate_response(self, query: str, relevant_chunks: List[str]) -> str:
        try:
            if not relevant_chunks:
                return "I cannot answer this question as no relevant content was found in the PDF."
            ctx = "\n".join(relevant_chunks)
            prompt = f"Answer using ONLY the context; if missing say you don't know.\nContext:\n{ctx}\nQuestion: {query}\nAnswer:"
            res = self.model.generate_content(prompt)
            return res.text or "I apologize, but I was unable to generate a response. Please try rephrasing your question."
        except Exception as e:
            raise PDFProcessingError(f"Error generating response: {str(e)}")

    async def process_pdf_with_fallback(self, pdf_content: bytes, filename: str = None) -> Tuple[str, dict]:
        
        try:
            text, info = await self.extract_text_from_pdf(pdf_content, filename)
            return text, info
        except PartialReadError:
            try:
                r = PyPDF2.PdfReader(io.BytesIO(pdf_content))
                t = ""; rp = 0; tp = len(r.pages)
                for p in r.pages:
                    try:
                        s = p.extract_text()
                        if s and s.strip(): t += s + "\n"; rp += 1
                    except Exception: continue
                if t.strip():
                    return t.strip(), {"total_pages": tp, "readable_pages": rp, "text_length": len(t), "partial_read": True, "fallback_used": True}
                raise EmptyPDFError()
            except Exception:
                raise EmptyPDFError()
        except Exception:
            raise

pdf_processor = PDFProcessor()