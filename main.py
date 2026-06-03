from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from app.models.database import ping_mongodb
import os
from dotenv import load_dotenv

# for reading .env file data
load_dotenv()

app = FastAPI()


@app.on_event("startup")
async def startup_event():
    await ping_mongodb()

    # required_env_vars = ["PINECONE_API_KEY", "OPENAI_API_KEY", "PINECONE_INDEX_NAME"]
    # missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    # if missing_vars:
    #     print(f"CRITICAL WARNING: Missing environment configuration keys: {missing_vars}")
    # else:
    #     print("Initialization complete. All critical API keys are set up.")


@app.get('/', tags=["Health"])
def root():

    return JSONResponse(status_code=200, content={"message": f"Everything is working fine: {os.environ.get("MONGO_URL")}"})


@app.post('/upload')
def file_upload():
    pass