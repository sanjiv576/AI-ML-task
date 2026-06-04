from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.models.database import ping_mongodb
from app.api.routes_ingest import router as ingest_router
from app.api.routes_chat import router as chat_router
# from app.api.routes_interview_booking import router as interview_booking_router
import os
from dotenv import load_dotenv

# for reading .env file data
load_dotenv()

app = FastAPI()

app.include_router(ingest_router)
app.include_router(chat_router)
# commenting interview booking route because booking is done from the conversation using LLM
# app.include_router(interview_booking_router)


@app.on_event("startup")
async def startup_event():
    await ping_mongodb()

    required_env_vars = ["PINECONE_API_KEY",
                         "GROQ_API_KEY", "PINECONE_INDEX_NAME"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        print(
            f"CRITICAL WARNING: Missing environment configuration keys: {missing_vars}")
    else:
        print("Initialization complete. All critical API keys are set up.")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTPException",
            "status_code": exc.status_code,
            "detail": exc.detail,
            "message": "Request failure. Check endpoint and payload format."
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "RequestValidationError",
            "detail": exc.errors(),
            "body": exc.body,
            "message": "Invalid request body or query parameters. Please send valid JSON."
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "detail": str(exc),
            "message": "The server encountered an unexpected error."
        }
    )


@app.get('/', tags=["Health"])
def root():
    return JSONResponse(status_code=200, content={"message": f"Server is live"})
