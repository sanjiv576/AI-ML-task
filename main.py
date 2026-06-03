from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()


@app.get('/')
def home():
    return JSONResponse(status_code=200, content={"message": "Everything is working fine."})
