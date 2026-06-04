
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from app.models.schemas import IngestResponse, InterviewBookingSchema, ChunkingStrategy
from app.models.database import insert_document_metadata
from app.services.extractor import TextExtractorService
from app.services.chunking import ChunkingService
from app.services.vector_store import VectorStoreServices

router = APIRouter(prefix="/api", tags=["Ingestion"])
vector_store_service = VectorStoreServices()


@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_document(
        file: UploadFile = File(...),
        strategy: ChunkingStrategy = Form(...)) -> IngestResponse:

    # extracts the text
    raw_text = await TextExtractorService.extract_text(file)

    try:
        chunks = ChunkingService.chunk_document(
            text=raw_text, strategy=strategy.value)
    except ValueError as err:
        print(f"Error while ingesting: {err}")
        raise HTTPException(status_code=400, detail=str(err))

    if not file.filename:
        raise HTTPException(
            status_code=400, detail="Uploaded file must have a filename")

    # insert document's metadata into mongoDB
    document_id = await insert_document_metadata(
        filename=file.filename,
        strategy=strategy.value,
        chunk_count=len(chunks)
    )
    # insert chunks (text) into Pinecone
    try:
        indexed_count = await vector_store_service.upsert_chunks(chunks, document_id)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Pinecone error: {str(e)}")

    return IngestResponse(
        document_id=document_id,
        filename=file.filename,
        strategy_used=strategy,
        chunk_count=indexed_count,
        message="Document ingested succesfully."
    )
