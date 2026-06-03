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
