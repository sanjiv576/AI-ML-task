""" Using Redis for chat memory"""

import json
import logging
import os
import redis.asyncio as redis
from typing import Dict, List
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


class ChatMemoryService:
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.ttl_seconds = 3600
        self.redis_available = True

    async def get_history(self, session_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """gets the history of the user

        Args:
            session_id (str): unique session identifier
            limit (int, optional): limits in int. Defaults to 10.

        Returns:
            List[Dict[str, str]]: list of message in dictionary formats
        """

        if not self.redis_available:
            return []

        redis_key = f"chat_session:{session_id}"
        try:
            raw_messages = await self.redis_client.lrange(redis_key, -limit, -1)
        except Exception as exc:
            logger.warning("Redis unavailable for get_history: %s", exc)
            self.redis_available = False
            return []

        history = []
        for msg in raw_messages:
            try:
                history.append(json.loads(msg))
            except json.JSONDecodeError:
                continue
        return history

    async def add_message(self, session_id: str, role: str, content: str) -> None:
        if not self.redis_available:
            return

        redis_key = f"chat_session:{session_id}"
        message_date = json.dumps({"role": role, "content": content})
        try:
            await self.redis_client.rpush(redis_key, message_date)
            await self.redis_client.expire(redis_key, self.ttl_seconds)
        except Exception as exc:
            logger.warning("Redis unavailable for add_message: %s", exc)
            self.redis_available = False

    async def close_connection(self):
        if self.redis_client:
            try:
                await self.redis_client.aclose()
            except Exception:
                pass
