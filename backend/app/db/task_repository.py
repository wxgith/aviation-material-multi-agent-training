from __future__ import annotations

from datetime import datetime
import json
from typing import Any

from app.db.database import init_db, session_scope
from app.db.models import AsyncTaskORM
from app.db.repositories import db_enabled


INTERRUPTIBLE_STATUSES = {"queued", "running", "cancelling"}


def save_task_snapshot(payload: dict[str, Any]) -> bool:
    if not db_enabled():
        return False
    try:
        init_db()
        with session_scope() as session:
            row = (
                session.query(AsyncTaskORM)
                .filter(AsyncTaskORM.task_id == payload["task_id"])
                .one_or_none()
            )
            if row is None:
                row = AsyncTaskORM(task_id=payload["task_id"])
                session.add(row)
            row.task_type = payload["task_type"]
            row.status = payload["status"]
            row.progress = int(payload.get("progress") or 0)
            row.message = payload.get("message", "")
            row.detail = payload.get("detail", "")
            row.current_agent = payload.get("current_agent", "")
            row.step_index = int(payload.get("step_index") or 0)
            row.total_steps = int(payload.get("total_steps") or 0)
            row.created_at_text = payload.get("created_at", "")
            row.started_at_text = payload.get("started_at", "")
            row.completed_at_text = payload.get("completed_at", "")
            row.updated_at_text = payload.get("updated_at", "")
            row.elapsed_ms = int(payload.get("elapsed_ms") or 0)
            row.step_timings = _json(payload.get("step_timings", []))
            row.result_payload = _json(payload.get("result"))
            row.error = payload.get("error", "")
            row.metadata_payload = _json(payload.get("metadata", {}))
            row.request_payload = _json(payload.get("request_payload", {}))
            row.events_payload = _json(payload.get("events", []))
            row.retry_of = payload.get("retry_of", "")
            row.updated_at = datetime.utcnow()
        return True
    except Exception:
        return False


def task_persistence_status() -> dict[str, Any]:
    if not db_enabled():
        return {"enabled": False, "connected": False, "table_ready": False}
    try:
        init_db()
        with session_scope() as session:
            session.query(AsyncTaskORM.id).limit(1).all()
        return {"enabled": True, "connected": True, "table_ready": True}
    except Exception:
        return {"enabled": True, "connected": False, "table_ready": False}


def load_task_snapshot(task_id: str) -> dict[str, Any] | None:
    if not db_enabled():
        return None
    try:
        init_db()
        with session_scope() as session:
            row = (
                session.query(AsyncTaskORM)
                .filter(AsyncTaskORM.task_id == task_id)
                .one_or_none()
            )
            return _payload(row) if row else None
    except Exception:
        return None


def mark_incomplete_tasks_interrupted() -> int:
    if not db_enabled():
        return 0
    try:
        init_db()
        with session_scope() as session:
            rows = (
                session.query(AsyncTaskORM)
                .filter(AsyncTaskORM.status.in_(INTERRUPTIBLE_STATUSES))
                .all()
            )
            for row in rows:
                row.status = "interrupted"
                row.message = "任务因后端重启中断"
                row.detail = "已保留重启前的进度和事件，可使用重试重新执行原请求。"
                row.completed_at_text = datetime.utcnow().isoformat() + "Z"
                row.updated_at_text = row.completed_at_text
                row.updated_at = datetime.utcnow()
                events = _loads(row.events_payload, [])
                events.append(
                    {
                        "event_id": len(events),
                        "event_type": "interrupted",
                        "task_id": row.task_id,
                        "task_type": row.task_type,
                        "status": "interrupted",
                        "progress": row.progress,
                        "message": row.message,
                        "detail": row.detail,
                        "current_agent": row.current_agent,
                        "step_index": row.step_index,
                        "total_steps": row.total_steps,
                        "timestamp": row.updated_at_text,
                        "elapsed_ms": row.elapsed_ms,
                        "step_timings": _loads(row.step_timings, []),
                    }
                )
                row.events_payload = _json(events)
            return len(rows)
    except Exception:
        return 0


def _payload(row: AsyncTaskORM) -> dict[str, Any]:
    return {
        "task_id": row.task_id,
        "task_type": row.task_type,
        "status": row.status,
        "progress": row.progress,
        "message": row.message,
        "detail": row.detail,
        "current_agent": row.current_agent,
        "step_index": row.step_index,
        "total_steps": row.total_steps,
        "created_at": row.created_at_text,
        "started_at": row.started_at_text,
        "completed_at": row.completed_at_text,
        "updated_at": row.updated_at_text,
        "elapsed_ms": row.elapsed_ms,
        "step_timings": _loads(row.step_timings, []),
        "result": _loads(row.result_payload, None),
        "error": row.error,
        "cancel_requested": False,
        "metadata": _loads(row.metadata_payload, {}),
        "request_payload": _loads(row.request_payload, {}),
        "retry_of": row.retry_of,
        "events": _loads(row.events_payload, []),
    }


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=_json_default)


def _json_default(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _loads(value: str, default: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default
