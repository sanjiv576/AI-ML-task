import os
import json
from typing import List, Dict, Tuple, Any, cast
from groq import AsyncGroq
from app.services.vector_store import VectorStoreServices
from app.models.schemas import InterviewBookingSchema
from app.models.database import insert_interview_booking
from dotenv import load_dotenv

load_dotenv()


class LLMRagService:
    def __init__(self):
        self.groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.vector_store = VectorStoreServices()
        self.llm_model = "llama-3.1-8b-instant"
        # self.llm_model = "llama-3.3-70b-versatile"

    async def _retrieve_context(self, query: str, top_k: int = 3) -> str:
        search_results = self.vector_store.index.search(
            inputs={"text": query},
            top_k=top_k,
            namespace="__default__"
        )

        context_chunks = []

        try:
            hits = search_results["result"]["hits"]
            for match in hits:
                text_content = match["fields"].get("text")
                if text_content:
                    context_chunks.append(text_content)

        except (KeyError, TypeError, AttributeError) as err:
            print(f"Search parsing error: {err}")

        return "\n\n---\n\n".join(context_chunks)

    def _get_booking_tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",  
            "function": {       
                "name": "book_interview",
                "description": "Registers an interview booking in the system.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string", "format": "email"},
                        "date": {"type": "string"},
                        "time": {"type": "string"}
                    },
                    "required": ["name", "email", "date", "time"]
                }
            }
        }

    async def execute_rag(self, user_query: str, chat_history: List[Dict[str, str]]) -> Tuple[str, bool]:
        retrieved_context = await self._retrieve_context(user_query)

        system_prompt = (
            "You are an expert AI recruiting assistant.\n\n"
            f"CONTEXT:\n{retrieved_context}\n\n"
            "RULES: If the candidate wants to book an interview, collect their name, email, date, and time. "
            "Only invoke the `book_interview` tool when you have all 4 required parameters."
        )

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt}]
        for msg in chat_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_query})

        response = await self.groq_client.chat.completions.create(
            model=self.llm_model,
            messages=cast(Any, messages),
            tools=cast(Any, [self._get_booking_tool_definition()]),
            tool_choice="auto"
        )

        response_message = response.choices[0].message
        tool_calls = getattr(response_message, "tool_calls", []) or []
        booking_triggered = False

        if tool_calls:
            for tool_call in tool_calls:
                if getattr(tool_call, "name", None) == "book_interview":
                    try:
                        arguments = tool_call.arguments
                        if isinstance(arguments, str):
                            arguments = json.loads(arguments)
                        booking_payload = InterviewBookingSchema(**arguments)
                        booking_triggered = await insert_interview_booking(booking_payload)
                        tool_result = "Success: Booking recorded securely in MongoDB." if booking_triggered else "Error."
                    except Exception as e:
                        tool_result = f"Validation Error: {str(e)}"

                    messages.append(
                        {"role": "assistant", "content": response_message.content or ""})
                    messages.append({
                        "role": "tool",
                        "tool_call_id": getattr(tool_call, "id", None),
                        "name": "book_interview",
                        "content": tool_result
                    })

                    second_response = await self.groq_client.chat.completions.create(
                        model=self.llm_model,
                        messages=cast(Any, messages)
                    )
                    return second_response.choices[0].message.content or "", booking_triggered

        return response_message.content or "", booking_triggered
