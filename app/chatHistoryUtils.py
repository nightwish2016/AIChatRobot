import datetime
from typing import Optional, List, Dict
from app.DB.SqlLiteUtil import SqlLiteUtil

class chatHistoryUtils:
    def __init__(self):
        self.db = SqlLiteUtil()

    #  userid, role, model,promptTokens ,CompletionTokens ,TotalTokens,Created,GptContent,Prompt,SessionId 
    def insertChatHistory(self ,pars   ):
        self.db.insertChatHistory(pars)

    def insertImageHistory(self ,pars   ):
        self.db.insertImageHistory(pars)

    def insertTtsHistory(self ,pars):
        self.db.insertTtsHistory(pars)
    def insertTranscriptionHistory(self ,pars):
        self.db.insertTranscriptionHistory(pars)

    def _generate_session_title(self, text: Optional[str]) -> str:
        if not text:
            return "新的对话"
        cleaned = text.strip()
        if not cleaned:
            return "新的对话"
        first_line = cleaned.splitlines()[0].strip()
        candidate = first_line if first_line else cleaned.replace("\n", " ").strip()
        candidate = candidate.replace("\r", " ").strip()
        if len(candidate) > 30:
            candidate = candidate[:30].rstrip() + "..."
        return candidate or "新的对话"

    def _generate_preview_text(self, text: Optional[str]) -> str:
        if not text:
            return ""
        cleaned = text.strip().replace("\r", " ")
        cleaned = " ".join(cleaned.split())
        if len(cleaned) > 60:
            cleaned = cleaned[:60].rstrip() + "..."
        return cleaned

    def get_session_history(self, user_id: int, session_id: Optional[str] = None, limit: int = 50) -> Dict[str, Optional[str]]:
        db = SqlLiteUtil()
        try:
            active_session_id = session_id
            if not active_session_id:
                session_rows = db.query(
                    """
                    SELECT SessionId
                    FROM chatHistory
                    WHERE UserId = ?
                    ORDER BY Created DESC, Id DESC
                    LIMIT 1
                    """,
                    (user_id,),
                )
                if session_rows:
                    active_session_id = session_rows[0]["SessionId"]

            if not active_session_id:
                return {"session_id": None, "messages": []}

            message_rows = db.query(
                """
                SELECT Id, Role, Model, Prompt, GptContent, Created
                FROM chatHistory
                WHERE UserId = ? AND SessionId = ?
                ORDER BY Created ASC, Id ASC
                LIMIT ?
                """,
                (user_id, active_session_id, limit),
            )

            messages = []
            for row in message_rows:
                role = row["Role"]
                raw_content_prompt = row["Prompt"] or ""
                raw_content_assistant = row["GptContent"] or ""
                content = raw_content_prompt if role == "user" else raw_content_assistant

                created_raw = row["Created"]
                created_ts = None
                created_iso = None
                if created_raw is not None:
                    try:
                        created_ts = int(created_raw)
                        created_iso = datetime.datetime.fromtimestamp(created_ts).isoformat()
                    except (ValueError, TypeError, OSError):
                        created_iso = str(created_raw)

                messages.append(
                    {
                        "role": role,
                        "content": content,
                        "model": row["Model"],
                        "created": created_ts,
                        "created_iso": created_iso,
                    }
                )

            return {
                "session_id": active_session_id,
                "messages": messages,
            }
        finally:
            db.cursor.close()
            db.conn.close()

    def list_recent_sessions(self, user_id: int, limit: int = 20) -> List[Dict[str, Optional[str]]]:
        db = SqlLiteUtil()
        try:
            session_rows = db.query(
                """
                SELECT SessionId, MAX(Created) AS LastCreated
                FROM chatHistory
                WHERE UserId = ?
                GROUP BY SessionId
                ORDER BY LastCreated DESC
                LIMIT ?
                """,
                (user_id, limit),
            )

            sessions: List[Dict[str, Optional[str]]] = []
            for row in session_rows:
                session_id = row["SessionId"]
                last_created = row["LastCreated"]
                last_iso = None
                if last_created is not None:
                    try:
                        last_iso = datetime.datetime.fromtimestamp(int(last_created)).isoformat()
                    except (ValueError, TypeError, OSError):
                        last_iso = str(last_created)

                title_row = db.query(
                    """
                    SELECT Role, Prompt, GptContent
                    FROM chatHistory
                    WHERE UserId = ? AND SessionId = ?
                      AND (
                        (Role = 'user' AND IFNULL(Prompt, '') <> '')
                        OR (Role <> 'user' AND IFNULL(GptContent, '') <> '')
                      )
                    ORDER BY Created ASC, Id ASC
                    LIMIT 2
                    """,
                    (user_id, session_id),
                )
                raw_title = ""
                raw_preview = ""
                if title_row:
                    for row_data in title_row:
                        if row_data["Role"] == "user" and not raw_title:
                            raw_title = row_data.get("Prompt") or ""
                        elif row_data["Role"] != "user" and not raw_preview:
                            raw_preview = row_data.get("GptContent") or ""
                    if not raw_title:
                        first_row = title_row[0]
                        raw_title = first_row.get("Prompt") or first_row.get("GptContent") or ""
                title = self._generate_session_title(raw_title)
                preview = self._generate_preview_text(raw_preview if raw_preview else raw_title)

                sessions.append(
                    {
                        "session_id": session_id,
                        "title": title,
                        "preview": preview,
                        "last_created": last_created,
                        "last_created_iso": last_iso,
                    }
                )

            return sessions
        finally:
            db.cursor.close()
            db.conn.close()
