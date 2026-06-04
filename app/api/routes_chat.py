from fastapi import APIRouter, HTTPException, status, Query
from app.models.schemas import ChatRequest, ChatResponse
from app.services.chat_memory import ChatMemoryService
from app.services.llm_rag import LLMRagService

router = APIRouter(prefix="/api", tags=["Conversational RAG"])
chat_memory_service = ChatMemoryService()
llm_rag_service = LLMRagService()


@router.post("/chat", response_model=ChatResponse)
async def process_chat_message(payload: ChatRequest, debug: bool = Query(False, description="Return debug info inline for testing")) -> ChatResponse:
    try:
        historical_context = await chat_memory_service.get_history(payload.session_id)

        ai_reply, booking_confirmed, debug_info = await llm_rag_service.execute_rag(
            payload.message,
            historical_context,
            debug=debug
        )

        await chat_memory_service.add_message(payload.session_id, "user", payload.message)
        await chat_memory_service.add_message(payload.session_id, "assistant", ai_reply)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # If debug requested, append debug info into the reply to avoid schema changes
    if debug and debug_info:
        ai_reply = f"[DEBUG] {debug_info}\n\n{ai_reply}"

    return ChatResponse(
        session_id=payload.session_id,
        reply=ai_reply,
        booking_confirmed=booking_confirmed
    )
