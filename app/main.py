# app/main.py
from fastapi import FastAPI
from .db.mongodb import MongoDB
import cloudinary
from .config import settings
from .api.endpoints import pdf

app = FastAPI(title="PDF Query System")

# Register routes
@app.get("/")
async def root():
    return {"message": "Welcome to the PDF Query System API!"}

app.include_router(pdf.router, prefix="/api/v1", tags=["pdf"])

@app.on_event("startup")
async def startup_db_client():
    await MongoDB.connect_db()
    
    # Configure Cloudinary
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET
    )

@app.on_event("shutdown")
async def shutdown_db_client():
    await MongoDB.close_db()