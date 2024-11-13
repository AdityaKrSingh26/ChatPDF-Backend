# app/api/endpoints/pdf.py
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from typing import List
from ...db.mongodb import MongoDB
import cloudinary.uploader
from ...config import settings
from ...schemas.models import PDFMetadata  # Import PDFMetadata here
import logging
from datetime import datetime
from bson import ObjectId

router = APIRouter()

@router.post("/upload_pdf", status_code=status.HTTP_201_CREATED)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file to Cloudinary and store metadata in MongoDB Atlas
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    try:
        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(
            file.file,
            resource_type="raw",
            folder="pdfs",
            allowed_formats=["pdf"],
            unique_filename=True,
            overwrite=False
        )
        
        # Save metadata to MongoDB Atlas
        pdf_id = await MongoDB.save_pdf_metadata(
            filename=file.filename,
            cloudinary_data=upload_result
        )
        
        return {
            "status": "success",
            "pdf_id": pdf_id,
            "filename": file.filename,
            "url": upload_result['secure_url']
        }
        
    except Exception as e:
        logging.error(f"Error uploading PDF: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading PDF file"
        )

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
            
        # Convert ObjectId to string for each document
        for pdf in pdfs:
            pdf['id'] = str(pdf.pop('_id'))
            
        return pdfs
        
    except Exception as e:
        logging.error(f"Error retrieving PDFs: {str(e)}")
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
        # Get PDF metadata from MongoDB
        pdf = await MongoDB.db.pdfs.find_one({"_id": ObjectId(pdf_id)})
        if not pdf:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PDF not found"
            )
            
        # Delete from Cloudinary
        cloudinary.uploader.destroy(pdf['cloudinary_public_id'])
        
        # Delete from MongoDB
        await MongoDB.db.pdfs.delete_one({"_id": ObjectId(pdf_id)})
        
        return {"status": "success", "message": "PDF deleted successfully"}
        
    except Exception as e:
        logging.error(f"Error deleting PDF: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting PDF"
        )