from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv


load_dotenv()

app = FastAPI()


@app.get('/')
def home():
    
    return JSONResponse(status_code=200, content={"message": f"Everything is working fine: {os.environ.get("MONGO_URL")}"})
