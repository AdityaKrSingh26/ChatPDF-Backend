# app/schemas/models.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Pydantic models for request and response payloads
class PDFMetadata(BaseModel):
    id: str
    filename: str
    cloudinary_url: str
    cloudinary_public_id: str
    file_size: int
    created_at: datetime
    format: str

class QueryRequest(BaseModel):
    pdf_id: str
    query: str

class QueryResponse(BaseModel):
    id: str
    pdf_id: str
    query: str
    response: str
    created_at: datetime