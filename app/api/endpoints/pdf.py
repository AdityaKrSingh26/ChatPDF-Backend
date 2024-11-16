from fastapi import APIRouter, UploadFile, File, HTTPException, status
from typing import List
from ...db.mongodb import MongoDB
import cloudinary.uploader
from ...config import settings
from ...schemas.models import PDFMetadata 
import logging
from datetime import datetime
from bson import ObjectId

router = APIRouter()

@router.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        # Check if the file is a PDF
        if not file.filename.endswith(".pdf"):
            print(f"Error: File {file.filename} is not a PDF.")
            raise HTTPException(
                status_code=400, 
                detail="Only PDF files are allowed."
            )

        # Step 1: Upload PDF file to Cloudinary
        try:
            # Uploading file to Cloudinary...
            upload_result = cloudinary.uploader.upload(
                file.file,
                resource_type="raw"
            )
        except Exception as upload_error:
            print(f"Cloudinary upload failed: {upload_error}")
            raise HTTPException(
                status_code=500, 
                detail="Error uploading file to Cloudinary."
            )

        # Step 2: Prepare metadata from Cloudinary upload result
        cloudinary_data = {
            'filename': file.filename,
            'cloudinary_url': upload_result['secure_url'],
            'cloudinary_public_id': upload_result['public_id'],
            'file_size': upload_result['bytes'],  # This is the correct field name
            'created_at': datetime.strptime(upload_result['created_at'], "%Y-%m-%dT%H:%M:%SZ"),
            'format': upload_result.get('format', file.filename.split('.')[-1])
        }

        # Step 3: Store the PDF metadata in MongoDB
        try:
            pdf_id = await MongoDB.save_pdf_metadata(
                file.filename, 
                cloudinary_data
            )
        except Exception as db_error:
            print(f"Error saving metadata to MongoDB: {db_error}")
            raise HTTPException(
                status_code=500, 
                detail=str(db_error)
            )

        # Step 4: Prepare response
        response = {
            "status": "success",
            "message": f"PDF '{file.filename}' uploaded and processed successfully.",
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

        return response

    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        print(f"Error in upload_pdf endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))



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