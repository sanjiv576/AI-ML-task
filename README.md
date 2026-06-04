

## Overview

This backend is a FastAPI service for a conversational Retrieval-Augmented Generation (RAG) application. It supports document ingestion, text chunking, embedding storage, conversational chat with contextual retrieval, Redis chat memory, and interview booking via natural language.

The backend is running live at:

https://rag-bot-zgs8.onrender.com/

## Purpose

This backend enables users to:

- Upload `.pdf` or `.txt` documents for ingestion
- Automatically extract text and split it into chunks using selectable chunking strategies
- Store metadata in MongoDB and document chunks in Pinecone for semantic search
- Chat with the system using conversational RAG
- Maintain multi-turn conversation context via Redis
- Book interview slots through chat using the LLM and persist booking data in MongoDB

## Key Features

- **Document Ingestion**
  - Extracts text from `.pdf` and `.txt`
  - Supports two chunking strategies: fixed-character and token-based semantic chunking
  - Stores document metadata in MongoDB
  - Saves chunk records to Pinecone for vector search

- **Conversational RAG**
  - Custom RAG implementation without RetrievalQAChain
  - Retrieves relevant context from Pinecone using vector search
  - Uses Groq LLM service for chat completions
  - Supports multi-turn chat using Redis memory storage

- **Interview Booking**
  - Detects booking intent from chat messages
  - Extracts name, email, date, and time from user input
  - Saves booking details into MongoDB
  - Handles direct booking when all details are provided in a single message

- **Error handling**
  - Global FastAPI error handlers for validation and internal server errors
  - Prevents backend crashes on malformed JSON or invalid requests

## Packages and Their Roles

- `fastapi` — Web framework for API endpoints
- `uvicorn` — ASGI server for local development and deployment
- `python-dotenv` — Loads environment variables from `.env`
- `motor` — Async MongoDB client for metadata and bookings
- `pymongo` — MongoDB interaction utility
- `redis` — Async Redis client for chat memory storage
- `pinecone` — Pinecone vector database client for storing and searching embeddings
- `groq` — Groq AI client for LLM chat completions
- `pdfplumber` — PDF text extraction library
- `tiktoken` — Tokenization for semantic chunking
- `pydantic` — Request/response validation and schema models
- `python-multipart` — File upload support for FastAPI

## Endpoints

### `GET /`

Health check endpoint.

- Returns a simple JSON message to confirm the backend is live.

### `POST /api/ingest`

Upload a document and ingest it into the vector store.

- Accepts: `file` (UploadFile), `strategy` (form field)
- Supported file formats: `.pdf`, `.txt`
- Stores metadata in MongoDB and vector chunks in Pinecone

### `POST /api/chat`

Send a chat message to the conversational RAG system.

- Accepts JSON: `session_id`, `message`
- Optional query parameter: `debug=true` for inline debug details
- Uses Redis for chat history and Groq LLM for responses
- Returns AI reply and booking confirmation status

### `POST /api/interview_booking`

Create an interview booking directly.

- Accepts: `name`, `email`, `date`, `time`
- Saves booking details in MongoDB

## Notes

- The backend currently uses MongoDB for metadata and booking persistence.
- Pinecone is used for vector storage and semantic retrieval.
- Redis is used to maintain conversation state across turns.
- Interview booking is supported through chat and direct booking endpoint.

## Running Locally

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start Redis locally or via Docker:

```bash
docker run --name redis -p 6379:6379 -d redis
```

3. Start the API server:

```bash
uvicorn main:app --reload
```

## Live Backend

The service is deployed at:

https://rag-bot-zgs8.onrender.com/
