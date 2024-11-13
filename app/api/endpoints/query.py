# app/api/endpoints/query.py
from fastapi import APIRouter, HTTPException, status
from ...schemas.models import QueryRequest, QueryResponse
from ...db.mongodb import MongoDB
from ...utils.pdf_processor import pdf_processor
import cloudinary.api
from datetime import datetime
from bson import ObjectId
from typing import List

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
async def query_pdf(request: QueryRequest):
    try:
        # Validate PDF exists
        pdf = await MongoDB.db.pdfs.find_one({"_id": ObjectId(request.pdf_id)})
        if not pdf:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PDF not found"
            )
            
        # Download PDF from Cloudinary
        cloudinary_response = cloudinary.api.resource(
            pdf['cloudinary_public_id'],
            resource_type="raw"
        )
        
        # Extract text from PDF
        pdf_content = await cloudinary.api.download(cloudinary_response['secure_url'])
        pdf_text = await pdf_processor.extract_text_from_pdf(pdf_content)
        
        # Create chunks
        chunks = pdf_processor.create_chunks(pdf_text)
        
        # Find relevant chunks
        relevant_chunks = await pdf_processor.find_relevant_chunks(
            request.query,
            chunks
        )
        
        # Generate response
        response_text = await pdf_processor.generate_response(
            request.query,
            relevant_chunks
        )
        
        # Save query and response to MongoDB
        query_doc = {
            "pdf_id": request.pdf_id,
            "query": request.query,
            "response": response_text,
            "created_at": datetime.utcnow()
        }
        
        result = await MongoDB.db.queries.insert_one(query_doc)
        
        return {
            "id": str(result.inserted_id),
            "pdf_id": request.pdf_id,
            "query": request.query,
            "response": response_text,
            "created_at": query_doc["created_at"]
        }
        
    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )

@router.get("/history/{pdf_id}", response_model=List[QueryResponse])
async def get_query_history(pdf_id: str, skip: int = 0, limit: int = 10):
    try:
        # Validate PDF exists
        pdf = await MongoDB.db.pdfs.find_one({"_id": ObjectId(pdf_id)})
        if not pdf:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PDF not found"
            )
            
        # Get query history
        queries = await MongoDB.db.queries.find(
            {"pdf_id": pdf_id}
        ).sort(
            "created_at", -1
        ).skip(skip).limit(limit).to_list(length=None)
        
        return [
            {
                "id": str(query["_id"]),
                "pdf_id": query["pdf_id"],
                "query": query["query"],
                "response": query["response"],
                "created_at": query["created_at"]
            }
            for query in queries
        ]
        
    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving query history: {str(e)}"
        )