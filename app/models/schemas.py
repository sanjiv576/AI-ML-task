from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Annotated
from enum import Enum

# defining enum for two strategies ==> fixed, semantic


class ChunkingStrategy(str, Enum):
    FIXED = "fixed"
    SEMANTIC = "semantic"


# validating the inputs for uploading the file from the user

class IngestResponse(BaseModel):
    document_id: Annotated[str, Field(..., description="Unique id for the stored document", examples=[
                                      "T45S", "A7RE", "X89R"])]
    filename: Annotated[str,
                        Field(..., description="Name of the uploaded file")]
    strategy_used: ChunkingStrategy
    chunk_count: Annotated[int, Field(..., description="Number of vector chunks to be generated", gt=0, examples=[
                                      453, 101, 90])]
    message: Annotated[str, Field(
        default="Document successfully ingested and indexed.")]


# validating the input for requesting the chats from the user

class ChatRequest(BaseModel):
    session_id: Annotated[str,
                          Field(..., description="Unique identifier for the user's chat session")]
    message: Annotated[str, Field(..., description="User's question")]


# validating the out for response of the chat request from the server

class ChatResponse(BaseModel):
    session_id: Annotated[str,
                          Field(..., description="Unique identifier for the user's chat session")]
    reply: Annotated[str, Field(..., description="AI's response")]
    booking_confirmed: Annotated[bool, Field(..., description="", examples=[
                                             False, True],)]


# validating the interview booking as well

class InterviewBookingSchema(BaseModel):
    name: Annotated[str, Field(..., description="Full name of the candidate", examples=[
                               "Ram Rai", "Harka Shah"])]
    email: Annotated[EmailStr,
                     Field(..., description="Email of the candidate")]
    date: Annotated[str, Field(..., description="Date of the interview", examples=[
                               "2026-02-22"])]
    time: Annotated[str, Field(..., description="Time of the interview", examples=[
                               "10:00 AM", "12:30 PM"])]
