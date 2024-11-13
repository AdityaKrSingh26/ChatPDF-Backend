# app/db/mongodb.py
from motor.motor_asyncio import AsyncIOMotorClient
from ..config import settings
from bson import ObjectId

class MongoDB:
    client = None
    db = None

    @classmethod
    async def connect_db(cls):
        cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
        cls.db = cls.client[settings.DB_NAME]
        # Create indexes for better query performance
        await cls.db.pdfs.create_index("created_at")
        await cls.db.queries.create_index("created_at")
        
    @classmethod
    async def close_db(cls):
        if cls.client:
            await cls.client.close()
            
    @classmethod
    async def save_pdf_metadata(cls, filename: str, cloudinary_data: dict):
        pdf_doc = {
            "filename": filename,
            "cloudinary_url": cloudinary_data['secure_url'],
            "cloudinary_public_id": cloudinary_data['public_id'],
            "file_size": cloudinary_data['bytes'],
            "created_at": cloudinary_data['created_at'],
            "format": cloudinary_data['format']
        }
        result = await cls.db.pdfs.insert_one(pdf_doc)
        return str(result.inserted_id)