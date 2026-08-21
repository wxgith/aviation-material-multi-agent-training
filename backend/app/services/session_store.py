from uuid import uuid4


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, dict] = {}

    def create(self, session: dict) -> dict:
        session_id = str(uuid4())
        session["session_id"] = session_id
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> dict:
        if session_id not in self._sessions:
            raise KeyError(f"Unknown session_id: {session_id}")
        return self._sessions[session_id]

    def put(self, session: dict) -> dict:
        self._sessions[session["session_id"]] = session
        return session

    def list_summaries(self, limit: int = 30) -> list[dict]:
        items = list(self._sessions.values())[-limit:]
        items.reverse()
        return [
            {
                "session_id": item["session_id"],
                "profile_id": item["profile"].get("profile_id", ""),
                "domain": item["domain"],
                "learning_goal": item["learning_goal"],
                "status": "completed",
                "diagnosis_score": item["diagnosis_result"].score,
                "diagnosis_level": item["diagnosis_result"].level,
                "weak_points": item["diagnosis_result"].weak_points,
                "interaction_count": len(item.get("inquiry_history", [])),
                "created_at": "",
                "updated_at": "",
            }
            for item in items
        ]

    def clear(self) -> None:
        self._sessions.clear()


session_store = SessionStore()
