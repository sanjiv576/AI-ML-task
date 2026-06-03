from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import Dict, Any

import os
from dotenv import load_dotenv

import uuid
from datetime import datetime, timezone
from app.models.schemas import InterviewBookingSchema

load_dotenv()


MONGO_DETAILS = os.getenv("MONGO_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_DETAILS)
database = client.ai_internship_db

# defining collections

metadata_collection = database.get_collection("document_metadata")
bookings_collection = database.get_collection("interview_bookings")


# ping mongodb whether it is active or not
async def ping_mongodb():
    try:
        await client.admin.command('ping')
        print("MongoDB is connected successfully")
    except Exception as err:
        print(f"MongoDB connection failed: {err}")


# ========================================== database operations ==========================================

async def insert_document_metadata(filename: str, strategy: str, chunk_count: int) -> str:
    """inserts a document's metadata into MongoDB

    Args:
        filename (str): name of the uploaded file
        strategy (str): either 'fixed' or 'semantic'
        chunk_count (int): number of vector chunks to be generated

    Returns:
        str: document id
    """

    try:
        document_id = str(uuid.uuid4())
        print(f'uid: {document_id}')

        metadata_doc = {
            "_id": document_id,
            "filename": filename,
            "strategy": strategy,
            "chunk_count": chunk_count,
            "uploaded_at": datetime.now(timezone.utc).isoformat()
        }
        print(f"Metadata: {metadata_doc}")
        
        # insert doc metadata into db
        await metadata_collection.insert_one(metadata_doc)
        return document_id

    except Exception as err:
        print(f"Error while insert document metadata: {err}")
        return f"{err}"


async def insert_interview_booking(booking_data: InterviewBookingSchema) -> bool:
    """inserts a interview booking data

    Args:
        booking_data (InterviewBookingSchema0): interview booking data

    Returns:
        bool: True as successs, False as failed
    """

    try:

        # converting pydantic model into python dict
        booking_doc = booking_data.model_dump()
        booking_doc["created_at"] = datetime.now(timezone.utc).isoformat()

        result = await bookings_collection.insert_one(booking_doc)
        return result.acknowledged

    except Exception as err:
        print(f"Error while inserting interview booking: {err}")
        return False
