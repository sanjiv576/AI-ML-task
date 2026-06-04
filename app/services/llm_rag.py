import os
import json
import re
import logging
from typing import List, Dict, Tuple, Any, cast, Optional
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

    def _has_booking_intent(self, text: str) -> bool:
        # Consider intent present if booking and interview/meeting keywords appear anywhere (any order)
        has_book = bool(re.search(r"\b(book|schedule|arrange)\b", text, re.I))
        has_target = bool(re.search(r"\b(interview|meeting)\b", text, re.I))

        # Also consider it intent if user uses booking verb and provides all booking details (name, email, date, time)
        email_present = bool(
            re.search(r"[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}", text))
        date_present = bool(self._parse_date(text))
        time_present = bool(
            re.search(r"\b\d{1,2}(:\d{2})?\s*(AM|PM|am|pm)\b", text))
        name_present = bool(re.search(
            r"(?:name is|my name is|I am|I'm)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)", text, re.I))

        return (has_book and has_target) or (has_book and email_present and date_present and time_present and name_present)

    def _log_missing_booking_fields(self, combined_text: str, email_match, date_value, time_match, name_match) -> None:
        missing = []
        if not email_match:
            missing.append("email")
        if not date_value:
            missing.append("date")
        if not time_match:
            missing.append("time")
        if not name_match:
            missing.append("name")

        logger = logging.getLogger(__name__)
        logger.debug("Booking extraction failed. Missing fields: %s", missing)
        logger.debug(
            "Combined conversation text for extraction:\n%s", combined_text)

    def _parse_date(self, text: str) -> Optional[str]:
        iso_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
        if iso_match:
            return iso_match.group(0)

        month_names = {
            "january": 1, "february": 2, "march": 3, "april": 4,
            "may": 5, "june": 6, "july": 7, "august": 8,
            "september": 9, "october": 10, "november": 11, "december": 12
        }

        month_day_year_match = re.search(
            r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+"
            r"(\d{1,2})(?:st|nd|rd|th)?,?\s*(\d{4})\b",
            text,
            re.I
        )
        if month_day_year_match:
            month_name = month_day_year_match.group(1).lower()
            day = int(month_day_year_match.group(2))
            year = int(month_day_year_match.group(3))
            month = month_names.get(month_name)
            if month:
                return f"{year:04d}-{month:02d}-{day:02d}"

        day_month_year_match = re.search(
            r"\b(\d{1,2})(?:st|nd|rd|th)?\s+"
            r"(January|February|March|April|May|June|July|August|September|October|November|December),?\s*(\d{4})\b",
            text,
            re.I
        )
        if day_month_year_match:
            day = int(day_month_year_match.group(1))
            month_name = day_month_year_match.group(2).lower()
            year = int(day_month_year_match.group(3))
            month = month_names.get(month_name)
            if month:
                return f"{year:04d}-{month:02d}-{day:02d}"

        return None

    def _extract_booking_details(self, messages: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
        # include all messages (user + assistant) since assistant may have asked about interviews
        combined_text = "\n".join([msg["content"] for msg in messages])

        if not self._has_booking_intent(combined_text):
            return None

        # get user's email, name, date, time from the messages
        email_match = re.search(
            r"[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}", combined_text)
        date_value = self._parse_date(combined_text)
        time_match = re.search(
            r"\b\d{1,2}(:\d{2})?\s*(AM|PM|am|pm)\b", combined_text)
        name_match = re.search(
            r"(?:name is|my name is|I am|I'm)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
            combined_text,
            re.I
        )

        if not (email_match and date_value and time_match and name_match):
            # record why extraction failed to help debug issues when Redis is down
            self._log_missing_booking_fields(
                combined_text, email_match, date_value, time_match, name_match)
            return None

        return {
            "name": name_match.group(1).strip(),
            "email": email_match.group(0).strip(),
            "date": date_value,
            "time": time_match.group(0).strip()
        }

    async def _try_direct_booking(self, user_query: str, chat_history: List[Dict[str, str]]) -> Tuple[Optional[str], bool, Optional[Dict[str, str]]]:
        booking_details = self._extract_booking_details(
            chat_history + [{"role": "user", "content": user_query}])
        debug_info: Optional[Dict[str, str]] = None
        if not booking_details:
            # include what was extracted for debugging
            debug_info = {"extracted": "none"}
            return None, False, debug_info

        try:
            booking_payload = InterviewBookingSchema(**booking_details)
            logger = logging.getLogger(__name__)
            logger.debug("Attempting direct booking with payload: %s",
                         booking_payload.model_dump())
            success = await insert_interview_booking(booking_payload)
            debug_info = {"extracted_name": booking_details.get("name", ""),
                          "extracted_email": booking_details.get("email", ""),
                          "extracted_date": booking_details.get("date", ""),
                          "extracted_time": booking_details.get("time", "")}
            if success:
                logger.info("Direct booking successful for %s",
                            booking_details.get("email"))
                return (
                    f"Interview booked for {booking_details['date']} at {booking_details['time']} under "
                    f"{booking_details['name']}. A confirmation email will be sent to {booking_details['email']}.",
                    True,
                    debug_info
                )
            else:
                logger.warning(
                    "Direct booking attempted but DB insert returned False: %s", debug_info)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.exception(
                "Exception while attempting direct booking: %s", e)

        return None, False, debug_info

    async def execute_rag(self, user_query: str, chat_history: List[Dict[str, str]], debug: bool = False) -> Tuple[str, bool, Optional[Dict[str, str]]]:
        direct_booking_response, direct_booking_triggered, direct_debug = await self._try_direct_booking(user_query, chat_history)
        if direct_booking_response:
            return direct_booking_response, direct_booking_triggered, (direct_debug if debug else None)
        retrieved_context = await self._retrieve_context(user_query)

        system_prompt = (
            "You are an expert AI recruiting assistant.\n\n"
            f"CONTEXT:\n{retrieved_context}\n\n"
            "RULES: If the candidate wants to book an interview, collect their name, email, date, and time. "
            "Once all 4 required parameters are available, invoke the `book_interview` tool immediately. "
            "Do not ask for any additional booking details after all four fields are provided."
        )

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt}]
        for msg in chat_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_query})

        try:
            response = await self.groq_client.chat.completions.create(
                model=self.llm_model,
                messages=cast(Any, messages),
                tools=cast(Any, [self._get_booking_tool_definition()]),
                tool_choice="auto"
            )
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.exception("LLM call failed: %s", e)
            # fallback: try direct booking from the user message
            direct_booking_response, direct_booking_triggered, direct_debug = await self._try_direct_booking(user_query, chat_history)
            if direct_booking_response:
                return direct_booking_response, direct_booking_triggered, (direct_debug if debug else None)
            # return a safe error message; include debug info if requested
            return ("Sorry, I couldn't process the request right now.", False, {"error": str(e)} if debug else None)

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
                    return second_response.choices[0].message.content or "", booking_triggered, None

        # final direct booking attempt (covers cases where tool wasn't used but details are present)
        direct_booking_response, direct_booking_triggered, direct_debug = await self._try_direct_booking(user_query, chat_history)
        if direct_booking_response:
            return direct_booking_response, direct_booking_triggered, (direct_debug if debug else None)

        return response_message.content or "", booking_triggered, None
