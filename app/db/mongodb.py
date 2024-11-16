import logging
from motor.motor_asyncio import AsyncIOMotorClient
from ..config import settings
import cloudinary
import cloudinary.uploader

class MongoDB:
    client = None
    db = None

    @classmethod
    async def connect_db(cls):
        try:
            # Step 1: Connect to MongoDB
            print("Step 1: Connecting to MongoDB...")
            cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
            cls.db = cls.client[settings.DB_NAME]
            await cls.db.pdfs.create_index("created_at")
            await cls.db.queries.create_index("created_at")
            print("MongoDB connected successfully!")

            # Step 2: Connect to Cloudinary
            print("Step 2: Connecting to Cloudinary...")
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET
            )
            print("Cloudinary connected successfully!")

        except Exception as e:
            print(f"Error connecting to MongoDB or Cloudinary: {str(e)}")
            logging.error(f"Error connecting to MongoDB or Cloudinary: {str(e)}")
            raise Exception("Database or Cloudinary connection failed")


    @classmethod
    async def save_pdf_metadata(cls, filename: str, cloudinary_data: dict):
        try:
            # Debugging log
            logger = logging.getLogger(__name__)
            logger.info(f"Saving metadata to MongoDB: {cloudinary_data}")
            
            # Create PDF document with correct field mapping
            pdf_doc = {
                "filename": filename,
                "cloudinary_url": cloudinary_data['cloudinary_url'],
                "cloudinary_public_id": cloudinary_data['cloudinary_public_id'],
                "file_size": cloudinary_data['file_size'],  # This matches the incoming data
                "created_at": cloudinary_data['created_at'],
                "format": cloudinary_data['format']
            }
            
            # Log the document to be inserted
            logger.info(f"PDF document to be inserted: {pdf_doc}")
            
            # Insert document into MongoDB
            result = await cls.db.pdfs.insert_one(pdf_doc)
            return str(result.inserted_id)
            
        except KeyError as ke:
            logger.error(f"Missing required field in cloudinary_data: {ke}")
            raise Exception(f"Missing required field in metadata: {ke}")
        except Exception as e:
            logger.error(f"Error saving PDF metadata: {str(e)}")
            raise Exception(f"Error saving PDF metadata to MongoDB: {str(e)}")