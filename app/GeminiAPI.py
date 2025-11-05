import datetime
import json
import logging
import os
import time
import uuid
from typing import Dict, List, Optional

import redis
from flask import Blueprint, session
from google import genai
from google.genai import types

from app.chatHistoryUtils import chatHistoryUtils
from app.session_title import SessionTitleManager

genminiai_bp = Blueprint("geminiai", __name__)
logger = logging.getLogger("log")


class GeminiAPI:
    def __init__(self) -> None:
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if google_api_key:
            genai.configure(api_key=google_api_key)
        else:
            logger.warning("GOOGLE_API_KEY is not set in the environment")
        try:
            self.client = genai.Client()
        except Exception as exc:
            logger.error("Failed to initialize Gemini client: %s", exc)
            self.client = None

    # ---------- Chat helpers ----------
    def _store_chat_log(
        self,
        session_id: str,
        user_id: int,
        role: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        created: int,
        gpt_content: str,
        prompt: str,
        charge_status: int,
    ) -> None:
        if not session_id or user_id is None:
            return
        params = (
            session_id,
            user_id,
            role,
            model_name,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            created,
            gpt_content,
            prompt,
            charge_status,
        )
        try:
            chatHistoryUtils().insertChatHistory(params)
        except Exception as exc:
            logger.exception(
                "Failed to persist Gemini chat history for session=%s role=%s: %s",
                session_id,
                role,
                exc,
            )

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // 4)

    def _normalize_model(self, model_name: str) -> str:
        return model_name or "gemini-1.5-flash"

    def _ensure_session_title(
        self,
        session_id: str,
        conversation_history: List[Dict[str, str]],
        fallback: str = "",
    ) -> None:
        try:
            SessionTitleManager().ensure_title(
                session_id,
                [{"role": msg.get("role", "user"), "content": msg.get("content", "")} for msg in conversation_history[:6]],
                fallback=fallback,
            )
        except Exception as exc:
            logger.debug("Skip Gemini session title generation: %s", exc)

    def _log_user_message(
        self, session_id: str, user_id: Optional[int], model_name: str, prompt: str
    ) -> None:
        if user_id is None:
            return
        created_timestamp = int(time.time())
        estimated_tokens = self._estimate_tokens(prompt)
        self._store_chat_log(
            session_id,
            user_id,
            "user",
            model_name,
            estimated_tokens,
            0,
            estimated_tokens,
            created_timestamp,
            prompt,
            prompt,
            0,
        )

    def _build_contents(self, conversation_history: List[Dict[str, str]]) -> List[types.Content]:
        contents: List[types.Content] = []
        for entry in conversation_history:
            role = entry.get("role", "user")
            content = entry.get("content", "") or ""
            if not content:
                continue
            contents.append(
                types.Content(
                    role="user" if role == "user" else "model",
                    parts=[types.Part(text=content)],
                )
            )
        return contents

    def _extract_text_from_response(self, response) -> str:
        if not response:
            return ""
        parts: List[str] = []
        if getattr(response, "text", None):
            parts.append(response.text)
        elif getattr(response, "candidates", None):
            for candidate in response.candidates or []:
                if not candidate or not getattr(candidate, "content", None):
                    continue
                for part in candidate.content.parts or []:
                    text = getattr(part, "text", None)
                    if text:
                        parts.append(text)
        return "".join(parts).strip()

    # ---------- Chat entry points ----------
    def chat_with_gemini(self, prompt: str, model: str):
        if not self.client:
            return {
                "error": "Gemini client not initialized",
                "statusCode": 500,
                "message": "Gemini client not initialized",
            }

        normalized_model = self._normalize_model(model)
        conversation_history = session.get("chatHistory") or []
        session_id = session.get("sessionid")
        if not session_id:
            session_id = str(uuid.uuid4())
            session["sessionid"] = session_id
            logger.info("Gemini chat created sessionid:%s", session_id)

        conversation_history.append({"role": "user", "content": prompt})
        session["chatHistory"] = conversation_history
        user_id = session.get("user_id")
        self._log_user_message(session_id, user_id, normalized_model, prompt)

        status_code = 200
        message = ""
        error = ""
        try:
            response = self.client.models.generate_content(
                model=normalized_model,
                contents=self._build_contents(conversation_history),
            )
            final_text = self._extract_text_from_response(response)
            if not final_text:
                final_text = "Gemini did not return any content. Please try again later."

            conversation_history.append({"role": "assistant", "content": final_text})
            session["chatHistory"] = conversation_history

            usage = getattr(response, "usage_metadata", None)
            prompt_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
            completion_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0
            total_tokens = getattr(usage, "total_token_count", prompt_tokens + completion_tokens)
            created_timestamp = int(time.time())

            if user_id is not None:
                self._store_chat_log(
                    session_id,
                    user_id,
                    "assistant",
                    normalized_model,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    created_timestamp,
                    final_text,
                    prompt,
                    1,
                )

            self._ensure_session_title(session_id, conversation_history, fallback=prompt)
            message = final_text
        except Exception as exc:
            logger.exception("Gemini chat failed: %s", exc)
            error = getattr(exc, "code", "gemini_error")
            status_code = getattr(exc, "status_code", 500)
            message = str(exc)

        if status_code != 200:
            return {"error": error, "statusCode": status_code, "message": message}
        return {"statusCode": status_code, "message": message}

    def chat_with_gemini_stream(self, prompt: str, model: str, session_dict: Dict[str, str]):
        if not self.client:
            yield "Gemini client is not initialized. Please check the configuration."
            return

        normalized_model = self._normalize_model(model)
        redis_client = redis.StrictRedis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0)),
        )

        conversation_id = session_dict["conversationid"]
        conversation_history = session_dict[f"conversation:{conversation_id}"]
        user_id = session_dict["user_id"]

        conversation_history.append({"role": "user", "content": prompt})
        self._log_user_message(conversation_id, user_id, normalized_model, prompt)

        try:
            stream = self.client.models.generate_content_stream(
                model=normalized_model,
                contents=self._build_contents(conversation_history),
            )

            final_text = ""
            usage = None
            for chunk in stream:
                usage = getattr(chunk, "usage_metadata", usage)
                chunk_text = getattr(chunk, "text", None) or self._extract_text_from_response(chunk)
                if not chunk_text:
                    continue
                if chunk_text.startswith(final_text):
                    delta = chunk_text[len(final_text):]
                else:
                    delta = chunk_text
                final_text += delta
                if delta:
                    yield delta

            if not final_text:
                final_text = "Gemini did not return any content. Please try again later."
                yield final_text

            prompt_tokens = getattr(usage, "prompt_token_count", 0) if usage else self._estimate_tokens(prompt)
            completion_tokens = getattr(usage, "candidates_token_count", 0) if usage else self._estimate_tokens(final_text)
            total_tokens = getattr(usage, "total_token_count", prompt_tokens + completion_tokens)
            created_timestamp = int(time.time())

            if user_id is not None:
                self._store_chat_log(
                    conversation_id,
                    user_id,
                    "assistant",
                    normalized_model,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    created_timestamp,
                    final_text,
                    prompt,
                    1,
                )

            convo_with_reply = conversation_history + [{"role": "assistant", "content": final_text}]
            self._ensure_session_title(conversation_id, convo_with_reply, fallback=prompt)

            conversation_history.append({"role": "assistant", "content": final_text})
            redis_client.hset("conversation_models", conversation_id, normalized_model)
            redis_client.set(
                f"conversation:{conversation_id}",
                json.dumps(conversation_history),
                ex=3600,
            )
        except Exception as exc:
            logger.exception("Gemini stream failed: %s", exc)
            error_code = getattr(exc, "code", "gemini_error")
            error_message = str(exc)
            yield f"{error_code}:{error_message}"

    # ---------- Existing voice generation ----------
    def generateVoice(self, text, voice_name):
        client = genai.Client()
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name,
                        )
                    )
                ),
            ),
        )

        print(response.usage_metadata.prompt_token_count)
        print(response.usage_metadata.candidates_token_count)
        print(response.usage_metadata.total_token_count)

        userId = session["user_id"]
        model = response.model_version
        complettionTokens = response.usage_metadata.candidates_token_count
        promptTokens = response.usage_metadata.prompt_token_count
        totalTokens = response.usage_metadata.total_token_count

        current_timestamp = time.time()
        created = current_timestamp
        chargeStatus = 1
        params = (
            userId,
            model,
            promptTokens,
            complettionTokens,
            totalTokens,
            created,
            chargeStatus,
        )

        u = chatHistoryUtils()
        u.insertTtsHistory(params)
        return response
