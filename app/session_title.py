import logging
import os
from typing import List, Dict, Optional

import redis
from flask import current_app

logger = logging.getLogger('log')


class SessionTitleManager:
    """Generates and caches concise conversation titles."""

    CACHE_KEY = "conversation_titles"

    def __init__(self) -> None:
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", 6379))
        db = int(os.getenv("REDIS_DB", 0))
        self.redis = redis.StrictRedis(host=host, port=port, db=db)
        self.model = os.getenv("SESSION_TITLE_MODEL", "gpt-4o-mini")

    def get_title(self, session_id: str) -> Optional[str]:
        if not session_id:
            return None
        cached = self.redis.hget(self.CACHE_KEY, session_id)
        if cached:
            try:
                return cached.decode("utf-8")
            except UnicodeDecodeError:
                return None
        return None

    def set_title(self, session_id: str, title: str) -> None:
        if not session_id or not title:
            return
        trimmed = title.strip()
        if not trimmed:
            return
        self.redis.hset(self.CACHE_KEY, session_id, trimmed[:60])

    def ensure_title(
        self,
        session_id: str,
        messages: Optional[List[Dict[str, str]]] = None,
        fallback: Optional[str] = None,
    ) -> Optional[str]:
        existing = self.get_title(session_id)
        if existing:
            return existing

        generated = self._generate_title_with_ai(messages or [])
        if not generated:
            generated = fallback or self._fallback_title(messages or [])

        if generated:
            self.set_title(session_id, generated)
        return generated

    def _generate_title_with_ai(self, messages: List[Dict[str, str]]) -> Optional[str]:
        formatted = self._format_messages(messages)
        if not formatted:
            return None
        try:
            prompt_text = (
                "请为下面的对话生成一个简短的标题，不超过12个中文字符或30个英文字符，"
                "不要包含引号、句号或冒号，只保留精炼的主题。\n\n"
                f"{formatted}"
            )
            response = current_app.openai.openai.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You generate concise, descriptive conversation titles.",
                    },
                    {
                        "role": "user",
                        "content": prompt_text,
                    },
                ],
                max_tokens=32,
                temperature=0.2,
            )
            title = response.choices[0].message.content.strip()
            return self._cleanup_title(title)
        except Exception as exc:
            logger.warning("Failed to generate session title via OpenAI: %s", exc)
            return None

    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        lines: List[str] = []
        for entry in messages[:6]:
            role = entry.get("role", "user").lower()
            content = (entry.get("content") or "").strip()
            if not content:
                continue
            label = "User" if role == "user" else "Assistant"
            lines.append(f"{label}: {content}")
        return "\n".join(lines)

    def _cleanup_title(self, title: str) -> str:
        cleaned = title.strip()
        cleaned = cleaned.strip("\"'“”‘’：:。,.!?")
        if len(cleaned) > 60:
            cleaned = cleaned[:60].rstrip()
        return cleaned

    def _fallback_title(self, messages: List[Dict[str, str]]) -> str:
        for entry in messages:
            if entry.get("role", "user") == "user":
                content = (entry.get("content") or "").strip()
                if content:
                    return content[:30]
        if messages:
            content = (messages[0].get("content") or "").strip()
            if content:
                return content[:30]
        return "新的对话"
