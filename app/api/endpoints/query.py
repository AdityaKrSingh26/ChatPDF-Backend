# app/api/endpoints/query.py
import requests
from fastapi import APIRouter, HTTPException, status
from ...schemas.models import QueryRequest, QueryResponse
from ...db.mongodb import MongoDB
from ...utils.pdf_processor import pdf_processor
import cloudinary.api
from datetime import datetime
from bson import ObjectId
from cloudinary.exceptions import NotFound
from typing import List

router = APIRouter()

import requests
from fastapi import APIRouter, HTTPException, status
from ...schemas.models import QueryRequest, QueryResponse
from ...db.mongodb import MongoDB
from ...utils.pdf_processor import pdf_processor
from datetime import datetime
from bson import ObjectId
from cloudinary.exceptions import NotFound
from typing import List

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
async def query_pdf(request: QueryRequest):
    try:
        # Validate PDF exists
        # print(f"Checking if PDF with ID {request.pdf_id} exists...")
        pdf = await MongoDB.db.pdfs.find_one({"_id": ObjectId(request.pdf_id)})
        if not pdf:
            print("PDF not found.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PDF not found"
            )
        # print("PDF found.")
        # print("PDF metadata:", pdf)

        # Download PDF from Cloudinary using requests
        # print(f"Downloading PDF from Cloudinary with ID: {pdf['cloudinary_public_id']}")
        try:
            # Use requests to download the PDF from Cloudinary URL
            pdf_content_response = requests.get(pdf['cloudinary_url'], stream=True)
            if pdf_content_response.status_code != 200:
                print(f"Failed to download PDF from Cloudinary. Status Code: {pdf_content_response.status_code}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Cloudinary resource not found"
                )
            pdf_content = pdf_content_response.content  # Get the raw content of the PDF
        except Exception as download_error:
            print(f"Error downloading PDF: {download_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error downloading PDF from Cloudinary"
            )

        # Proceed with the rest of your code for processing the PDF
        # print("Extracting text from PDF...")
        pdf_text = await pdf_processor.extract_text_from_pdf(pdf_content)
        # print("Extracted text:", pdf_text[:100], "...")  # Print only first 100 chars for brevity

        # Create chunks
        # print("Creating chunks from extracted text...")
        chunks = pdf_processor.create_chunks(pdf_text)
        print(f"Total chunks created: {len(chunks)}")

        # Find relevant chunks
        # print(f"Finding relevant chunks for query: '{request.query}'")
        relevant_chunks = await pdf_processor.find_relevant_chunks(
            request.query,
            chunks
        )
        print(f"Relevant chunks found: {len(relevant_chunks)}")

        # Generate response
        print("Generating response based on relevant chunks...")
        response_text = await pdf_processor.generate_response(
            request.query,
            relevant_chunks
        )
        print("Generated response:", response_text)

        # Save query and response to MongoDB
        print("Saving query and response to MongoDB...")
        query_doc = {
            "pdf_id": request.pdf_id,
            "query": request.query,
            "response": response_text,
            "created_at": datetime.utcnow()
        }
        result = await MongoDB.db.queries.insert_one(query_doc)
        print(f"Query saved with ID: {result.inserted_id}")

        return {
            "id": str(result.inserted_id),
            "pdf_id": request.pdf_id,
            "query": request.query,
            "response": response_text,
            "created_at": query_doc["created_at"]
        }

    except HTTPException as http_error:
        print("HTTP Exception occurred:", http_error.detail)
        raise http_error
    except Exception as e:
        print("Unexpected error occurred:", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )








@router.get("/history/{pdf_id}", response_model=List[QueryResponse])
async def get_query_history(pdf_id: str, skip: int = 0, limit: int = 10):
    try:
        # Validate PDF exists
        # print(f"Searching for PDF with id: {pdf_id}")
        pdf = await MongoDB.db.pdfs.find_one({"_id": ObjectId(pdf_id)})
        if not pdf:
            print("PDF not found.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PDF not found"
            )
        # else:
        #     print("PDF found.")

        # Get query history
        # print(f"Retrieving query history for PDF id: {pdf_id} with skip: {skip} and limit: {limit}")
        queries = await MongoDB.db.queries.find(
            {"pdf_id": pdf_id}
        ).sort(
            "created_at", -1
        ).skip(skip).limit(limit).to_list(length=None)

        # if queries:
        #     print(f"Found {len(queries)} queries for PDF id: {pdf_id}")
        # else:
        #     print("No queries found for this PDF.")

        # Construct the response
        response_data = [
            {
                "id": str(query["_id"]),
                "pdf_id": query["pdf_id"],
                "query": query["query"],
                "response": query["response"],
                "created_at": query["created_at"]
            }
            for query in queries
        ]
        # print("Returning response data:", response_data)
        return response_data

    except HTTPException as http_error:
        print("HTTP Exception occurred:", http_error.detail)
        raise http_error
    except Exception as e:
        print("Unexpected error occurred:", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving query history: {str(e)}"
        )
