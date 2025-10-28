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
import logging
from ...utils.pdf_processor import (
    CorruptedPDFError,
    PasswordProtectedPDFError,
    EmptyPDFError,
    PartialReadError,
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/query", response_model=QueryResponse)
async def query_pdf(request: QueryRequest):
    """
    Process PDF query with minimal error handling and graceful degradation
    """
    logger.info(f"Query start for PDF: {request.pdf_id}")
    
    try:
        # Validate PDF ID format
        if not ObjectId.is_valid(request.pdf_id):
            logger.error(f"Invalid PDF ID format: {request.pdf_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PDF ID format"
            )

        # Validate PDF exists in database
        pdf = await MongoDB.db.pdfs.find_one({
            "_id": ObjectId(request.pdf_id)
        })
        if not pdf:
            logger.error(f"PDF not found: {request.pdf_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PDF not found. Please ensure the PDF was uploaded successfully."
            )

        logger.info(f"PDF found: {pdf.get('filename', 'Unknown')}")

        # Download PDF from Cloudinary with retry logic
        pdf_content = None
        max_download_retries = 3
        
        for attempt in range(max_download_retries):
            try:
                logger.info(f"Downloading (attempt {attempt + 1}/{max_download_retries})")
                pdf_content_response = requests.get(
                    pdf['cloudinary_url'], 
                    stream=True,
                    timeout=30
                )
                
                if pdf_content_response.status_code == 200:
                    pdf_content = pdf_content_response.content
                    logger.info("Downloaded")
                    break
                else:
                    logger.warning(f"Download failed with status code: {pdf_content_response.status_code}")
                    if attempt < max_download_retries - 1:
                        continue
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="Failed to download PDF from storage. The file may have been deleted or moved."
                        )
                        
            except requests.exceptions.Timeout:
                logger.warning(f"Download timeout on attempt {attempt + 1}")
                if attempt < max_download_retries - 1:
                    continue
                else:
                    raise HTTPException(
                        status_code=status.HTTP_408_REQUEST_TIMEOUT,
                        detail="PDF download timed out. Please try again later."
                    )
            except Exception as download_error:
                logger.error(f"Download error on attempt {attempt + 1}: {str(download_error)}")
                if attempt < max_download_retries - 1:
                    continue
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Error downloading PDF from storage. Please try again later."
                    )

        if not pdf_content:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to download PDF content"
            )

        # Process PDF with enhanced error handling
        try:
            logger.info("Extracting text")
            pdf_text, processing_info = await pdf_processor.process_pdf_with_fallback(
                pdf_content, pdf.get('filename')
            )
            logger.info("Text extracted")
            
        except PasswordProtectedPDFError as e:
            logger.error(f"Password protected PDF: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This PDF is password protected and cannot be processed. Please upload an unprotected version."
            )
        except EmptyPDFError as e:
            logger.error(f"Empty PDF: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This PDF contains no readable text content. Please ensure the PDF has extractable text."
            )
        except CorruptedPDFError as e:
            logger.error(f"Corrupted PDF: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The PDF file appears to be corrupted and cannot be processed. Please try uploading a different file."
            )
        
        except PartialReadError as e:
            logger.warning(f"Partial read: {str(e)}")
            # Continue with partial content but inform user
            pdf_text, processing_info = await pdf_processor.process_pdf_with_fallback(
                pdf_content, pdf.get('filename')
            )

        # Create chunks from extracted text
        logger.info("Chunking text")
        chunks = pdf_processor.create_chunks(pdf_text)
        logger.info(f"Chunks: {len(chunks)}")

        if not chunks:
            logger.warning("No chunks created from PDF text")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to process the PDF content. The text may be too short or unreadable."
            )

        # Find relevant chunks
        logger.info("Ranking chunks")
        try:
            relevant_chunks = await pdf_processor.find_relevant_chunks(
                request.query,
                chunks
            )
            logger.info(f"Top chunks: {len(relevant_chunks)}")
        except Exception as e:
            logger.error(f"Error finding relevant chunks: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing your query. Please try again later."
            )

        # Generate response
        logger.info("Generating answer")
        try:
            response_text = await pdf_processor.generate_response(
                request.query,
                relevant_chunks
            )
            logger.info("Answer generated")
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error generating response. Please try rephrasing your question."
            )

        # Add processing info to response if partial read occurred
        if processing_info.get('partial_read', False):
            response_text += f"\n\nNote: Only {processing_info['readable_pages']}/{processing_info['total_pages']} pages were readable in this PDF."

        # Save query and response to MongoDB
        logger.info("Saving result")
        try:
            query_doc = {
                "pdf_id": request.pdf_id,
                "query": request.query,
                "response": response_text,
                "created_at": datetime.utcnow(),
                "processing_info": processing_info
            }
            result = await MongoDB.db.queries.insert_one(query_doc)
            logger.info(f"Saved ID: {result.inserted_id}")
        except Exception as e:
            logger.error(f"Error saving query: {str(e)}")
            # Don't fail the request if saving fails, just log it
            logger.warning("Query processing succeeded but failed to save to database")

        return {
            "id": str(result.inserted_id),
            "pdf_id": request.pdf_id,
            "query": request.query,
            "response": response_text,
            "created_at": query_doc["created_at"]
        }

    except HTTPException as http_error:
        logger.error(f"HTTP error during query processing: {http_error.detail}")
        raise http_error
    except Exception as e:
        logger.error(f"Unexpected error during query processing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your query. Please try again later."
        )


@router.get("/history/{pdf_id}", response_model=List[QueryResponse])
async def get_query_history(pdf_id: str, skip: int = 0, limit: int = 10):
    try:
        # Validate PDF exists
        pdf = await MongoDB.db.pdfs.find_one({"_id": ObjectId(pdf_id)})
        if not pdf:
            print("PDF not found.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PDF not found"
            )

        # Get query history from MongoDB and sort by created_at in descending order
        queries = await MongoDB.db.queries.find(
            {"pdf_id": pdf_id}
        ).sort(
            "created_at", -1
        ).skip(skip).limit(limit).to_list(length=None)

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