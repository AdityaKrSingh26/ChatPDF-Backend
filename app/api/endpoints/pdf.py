from fastapi import APIRouter, UploadFile, File, HTTPException, status
from typing import List
from ...db.mongodb import MongoDB
import cloudinary.uploader
from ...config import settings
from ...schemas.models import PDFMetadata 
import logging
from datetime import datetime
from bson import ObjectId
import io
import PyPDF2

try:
    import magic  # python-magic for MIME type detection
except Exception:
    magic = None

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload and minimally validate PDF file, then store metadata
    """
    logger.info(f"Upload start: {file.filename}")
    try:
        # Basic filename validation
        if not file.filename or not file.filename.endswith(".pdf"):
            logger.warning(f"Invalid filename: {file.filename}")
            raise HTTPException(
                status_code=400, 
                detail="Only PDF files are allowed. Please ensure your file has a .pdf extension."
            )

        # Read file content for validation
        file_content = await file.read()
        file_size = len(file_content)
        
        logger.info(f"Size: {file_size} bytes")
        
        # Minimal validations (keep endpoint simple)
        if file_size == 0 or file_size > 50 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size invalid or too large (max 50MB)"
            )
        if not file_content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Please upload a valid PDF."
            )
        # Light structural check
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            if getattr(reader, "is_encrypted", False):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Password-protected PDFs are not supported."
                )
            if len(reader.pages) > 1000:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="PDF has too many pages (max 1000)."
                )
        except PyPDF2.errors.PdfReadError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The PDF appears to be corrupted or unreadable."
            )

        # Reset file pointer for Cloudinary upload
        file.file.seek(0)

        # Upload to Cloudinary with error handling
        try:
            logger.info("Uploading to Cloudinary")
            upload_result = cloudinary.uploader.upload(
                file.file,
                resource_type="raw"
            )
            logger.info("Uploaded to Cloudinary")
        except Exception as upload_error:
            logger.error(f"Cloudinary upload failed: {upload_error}")
            raise HTTPException(
                status_code=500, 
                detail="Error uploading file to cloud storage. Please try again later."
            )

        # Prepare metadata
        cloudinary_data = {
            'filename': file.filename,
            'cloudinary_url': upload_result['secure_url'],
            'cloudinary_public_id': upload_result['public_id'],
            'file_size': upload_result['bytes'],
            'created_at': datetime.strptime(upload_result['created_at'], "%Y-%m-%dT%H:%M:%SZ"),
            'format': upload_result.get('format', file.filename.split('.')[-1])
        }

        # Store metadata in MongoDB
        try:
            logger.info("Saving metadata")
            pdf_id = await MongoDB.save_pdf_metadata(
                file.filename, 
                cloudinary_data
            )
            logger.info(f"Saved with ID: {pdf_id}")
        except Exception as db_error:
            logger.error(f"Database error: {db_error}")
            # Try to clean up Cloudinary upload
            try:
                cloudinary.uploader.destroy(upload_result['public_id'])
                logger.info("Cleaned up Cloudinary upload")
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup Cloudinary upload: {cleanup_error}")
            
            raise HTTPException(
                status_code=500, 
                detail="Error saving file metadata. Please try again later."
            )

        # Prepare response
        response = {
            "status": "success",
            "message": f"PDF '{file.filename}' uploaded and validated successfully.",
            "data": {
                "pdf_id": pdf_id,
                "pdf_metadata": {
                    "id": pdf_id,
                    "filename": file.filename,
                    "cloudinary_url": cloudinary_data['cloudinary_url'],
                    "cloudinary_public_id": cloudinary_data['cloudinary_public_id'],
                    "file_size": cloudinary_data['file_size'],
                    "created_at": cloudinary_data['created_at'],
                    "format": cloudinary_data['format']
                }
            }
        }

        logger.info(f"Upload completed: {file.filename}")
        return response

    except HTTPException as http_error:
        logger.error(f"HTTP error during PDF upload: {http_error.detail}")
        raise http_error
    except Exception as e:
        logger.error(f"Unexpected error during PDF upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="An unexpected error occurred during file upload. Please try again later."
        )



@router.get("/pdfs", response_model=List[PDFMetadata])
async def list_pdfs(skip: int = 0, limit: int = 10):
    """
    Retrieve list of uploaded PDFs with pagination
    """
    
    try:
        # Retrieve PDFs from MongoDB with pagination and sort by created_at
        pdfs = await MongoDB.db.pdfs.find() \
            .sort("created_at", -1) \
            .skip(skip) \
            .limit(limit) \
            .to_list(length=None)
        
        # Prepare and return response
        return [
            {**pdf, 'id': str(pdf.pop('_id'))}
            for pdf in pdfs
        ]
        
    except Exception as e:
        print(f"Error retrieving PDFs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving PDF list"
        )


@router.delete("/pdfs/{pdf_id}")
async def delete_pdf(pdf_id: str):
    """
    Delete PDF and associated queries from both Cloudinary and MongoDB.
    """
    try:
        # Step 1: Validate ObjectId format
        if not ObjectId.is_valid(pdf_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PDF ID format"
            )

        # Step 2: Get PDF metadata from MongoDB
        pdf = await MongoDB.db.pdfs.find_one({"_id": ObjectId(pdf_id)})
        if not pdf:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PDF not found"
            )
            
        # Step 3: Delete from Cloudinary
        cloudinary_result = cloudinary.uploader.destroy(pdf['cloudinary_public_id'])
        if cloudinary_result.get('result') == 'not found':
            print(f"PDF already deleted from Cloudinary")
        elif cloudinary_result.get('result') != 'ok':
            print(f"Failed to delete from Cloudinary: {cloudinary_result}")
            raise Exception("Failed to delete from Cloudinary")

        # Step 4: Delete associated queries from MongoDB
        query_result = await MongoDB.db.queries.delete_many({
            "pdf_id": pdf_id
        })
        
        # Step 5: Delete the PDF document itself from MongoDB
        pdf_result = await MongoDB.db.pdfs.delete_one({
            "_id": ObjectId(pdf_id)
        })
        if pdf_result.deleted_count == 0:
            raise Exception("Failed to delete PDF from MongoDB")
        
        return {
            "status": "success",
            "message": "PDF and associated queries deleted successfully",
            "pdf_id": pdf_id,
            "deleted_queries_count": query_result.deleted_count
        }
        
    except HTTPException as http_exc:
        raise http_exc
        
    except Exception as e:
        print(f"Error deleting PDF {pdf_id}: {e}")
        logging.error(f"Error deleting PDF {pdf_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting PDF: {str(e)}"
        )

@router.get("/pdfs_with_queries", response_model=List[dict])
async def list_pdfs_with_queries(skip: int = 0, limit: int = 10):
    """
    Retrieve a list of PDFs along with their query histories, with pagination.
    """

    try:
        # Retrieve PDFs from MongoDB with pagination and sort by created_at
        pdfs = await MongoDB.db.pdfs.find() \
            .sort("created_at", -1) \
            .skip(skip) \
            .limit(limit) \
            .to_list(length=None)
        
        # For each PDF, fetch its query history
        pdfs_with_queries = []
        for pdf in pdfs:
            pdf_id = str(pdf["_id"])
            # Retrieve queries associated with the current PDF
            queries = await MongoDB.db.queries.find(
                {"pdf_id": pdf_id}
            ).sort("created_at", -1).to_list(length=None)

            # Format the PDF and its associated queries
            pdf_data = {
                "id": pdf_id,
                "title": pdf.get("filename"),
                "created_at": pdf.get("created_at"),
                "queries": [
                    {
                        "id": str(query["_id"]),
                        "query": query["query"],
                        "response": query["response"],
                        "created_at": query["created_at"]
                    }
                    for query in queries
                ]
            }
            pdfs_with_queries.append(pdf_data)

        return pdfs_with_queries

    except HTTPException as http_error:
        print("HTTP Exception occurred:", http_error.detail)
        raise http_error

    except Exception as e:
        print("Unexpected error occurred:", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving PDFs with query history"
        )