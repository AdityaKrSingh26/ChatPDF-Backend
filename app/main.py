# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db.mongodb import MongoDB
import cloudinary
from .config import settings
from .api.endpoints import pdf, query  # Add query import

app = FastAPI(title="PDF Query System")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
@app.get("/")
async def root():
    return {"message": "Welcome to the PDF Query System API!"}

# Include routers
app.include_router(pdf.router, prefix="/api/v1", tags=["pdf"])
app.include_router(query.router, prefix="/api/v1", tags=["query"])  # Add query router

@app.on_event("startup")
async def startup_db_client():
    await MongoDB.connect_db()
    
    # Configure Cloudinary
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET
    )
    
    # Create MongoDB indexes for queries collection
    await MongoDB.db.queries.create_index("pdf_id")
    await MongoDB.db.queries.create_index("created_at")

@app.on_event("shutdown")
async def shutdown_db_client():
    print("Shutting down PDF Query System API")