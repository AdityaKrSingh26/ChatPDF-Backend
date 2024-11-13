# app/utils/pdf_processor.py
from typing import List, Dict
import PyPDF2
import io
import openai
from ..config import settings
import tiktoken
from typing import List, Dict
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

class PDFProcessor:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        self.encoding = tiktoken.get_encoding("cl100k_base")
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
        """Get embeddings for text using OpenAI's API"""
        try:
            response = await openai.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
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
        """Generate response using OpenAI's API"""
        try:
            # Combine relevant chunks
            context = "\n".join(relevant_chunks)
            
            # Create prompt
            prompt = f"""Given the following context from a PDF document:
            
            {context}
            
            Please answer the following question:
            {query}
            
            If the answer cannot be found in the context, please indicate that."""
            
            # Get response from OpenAI
            response = await openai.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided PDF content."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"Error generating response: {str(e)}")

pdf_processor = PDFProcessor()