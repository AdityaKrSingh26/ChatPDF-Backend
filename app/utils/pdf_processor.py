# app/utils/pdf_processor.py
from typing import List
import PyPDF2
import io
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from ..config import settings

class PDFProcessor:
    def __init__(self):
        # Initialize sentence-transformers model for embeddings
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        # Initialize Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')
        self.chunk_size = 1000
        self.chunk_overlap = 200
        
    async def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text content from PDF bytes"""
        try:
            pdf_file = io.BytesIO(pdf_content)
            reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")

    def create_chunks(self, text: str) -> List[str]:
        """Split text into chunks with overlap"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk = " ".join(words[i:i + self.chunk_size])
            chunks.append(chunk)
            
        return chunks

    async def get_embeddings(self, text: str) -> List[float]:
        """Get embeddings using sentence-transformers"""
        try:
            embedding = self.embedding_model.encode(text)
            return embedding.tolist()
        except Exception as e:
            raise Exception(f"Error getting embeddings: {str(e)}")

    async def find_relevant_chunks(self, query: str, chunks: List[str], top_k: int = 3) -> List[str]:
        """Find most relevant chunks for the query using cosine similarity"""
        try:
            # Get query embedding
            query_embedding = await self.get_embeddings(query)
            
            # Get embeddings for all chunks
            chunk_embeddings = []
            for chunk in chunks:
                embedding = await self.get_embeddings(chunk)
                chunk_embeddings.append(embedding)
            
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
            return [chunks[i] for i in top_indices]
            
        except Exception as e:
            raise Exception(f"Error finding relevant chunks: {str(e)}")

    async def generate_response(self, query: str, relevant_chunks: List[str]) -> str:
        """Generate response using Gemini Pro"""
        try:
            # Combine relevant chunks
            context = "\n".join(relevant_chunks)
            
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

Answer:"""
            
            # Generate response using Gemini
            response = self.model.generate_content(prompt)
            
            return response.text
            
        except Exception as e:
            raise Exception(f"Error generating response: {str(e)}")

pdf_processor = PDFProcessor()