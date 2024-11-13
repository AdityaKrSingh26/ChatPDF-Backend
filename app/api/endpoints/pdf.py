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
            raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
        
        print(f"Starting upload for file: {file.filename}")

        # Step 1: Upload PDF file to Cloudinary
        try:
            print("Uploading file to Cloudinary...")
            upload_result = cloudinary.uploader.upload(
                file.file,
                resource_type="raw"
            )
            print(f"File uploaded successfully. Cloudinary URL: {upload_result['secure_url']}")
        except Exception as upload_error:
            print(f"Cloudinary upload failed: {upload_error}")
            raise HTTPException(status_code=500, detail="Error uploading file to Cloudinary.")

        # Step 2: Prepare metadata from Cloudinary upload result
        cloudinary_data = {
            'filename': file.filename,
            'cloudinary_url': upload_result['secure_url'],
            'cloudinary_public_id': upload_result['public_id'],
            'file_size': upload_result['bytes'],  # This is the correct field name
            'created_at': datetime.strptime(upload_result['created_at'], "%Y-%m-%dT%H:%M:%SZ"),
            'format': upload_result.get('format', file.filename.split('.')[-1])
        }
        
        print(f"Prepared metadata: {cloudinary_data}")

        # Step 3: Store the PDF metadata in MongoDB
        try:
            print(f"Saving metadata for {file.filename} into MongoDB...")
            pdf_id = await MongoDB.save_pdf_metadata(file.filename, cloudinary_data)
            print(f"PDF metadata saved successfully with ID: {pdf_id}")
        except Exception as db_error:
            print(f"Error saving metadata to MongoDB: {db_error}")
            raise HTTPException(status_code=500, detail=str(db_error))

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
        pdfs = await MongoDB.db.pdfs.find() \
            .sort("created_at", -1) \
            .skip(skip) \
            .limit(limit) \
            .to_list(length=None)
            
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
    Delete PDF from both Cloudinary and MongoDB
    """
    
    try:
        # Validate ObjectId format
        if not ObjectId.is_valid(pdf_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PDF ID format"
            )

        # Get PDF metadata from MongoDB
        pdf = await MongoDB.db.pdfs.find_one({"_id": ObjectId(pdf_id)})
        if not pdf:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PDF not found"
            )
            
        # Delete from Cloudinary
        cloudinary_result = cloudinary.uploader.destroy(pdf['cloudinary_public_id'])
        if cloudinary_result.get('result') != 'ok':
            print(f"Failed to delete from Cloudinary: {cloudinary_result}")
            raise Exception("Failed to delete from Cloudinary")
            
        # Delete from MongoDB
        result = await MongoDB.db.pdfs.delete_one({"_id": ObjectId(pdf_id)})
        if result.deleted_count == 0:
            raise Exception("Failed to delete from MongoDB")
        
        return {
            "status": "success",
            "message": "PDF deleted successfully",
            "pdf_id": pdf_id
        }
        
    except HTTPException:
        raise
        
    except Exception as e:
        print(f"Error deleting PDF {pdf_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting PDF: {str(e)}"
        )