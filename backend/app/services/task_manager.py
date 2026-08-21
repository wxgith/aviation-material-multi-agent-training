from __future__ import annotations

from copy import copy
from datetime import datetime, timezone
import threading
import time
from typing import Any, Callable
from uuid import uuid4

from app.db.task_repository import (
    load_task_snapshot,
    mark_incomplete_tasks_interrupted,
    save_task_snapshot,
)


TERMINAL_STATUSES = {"completed", "failed", "cancelled", "interrupted"}


class TaskCancelled(RuntimeError):
    pass


TaskRunner = Callable[[Callable[..., None], Callable[[], bool]], Any]
TaskRunnerFactory = Callable[[dict[str, Any]], TaskRunner]


class TaskManager:
    def __init__(self) -> None:
        self._tasks: dict[str, dict[str, Any]] = {}
        self._runner_factories: dict[str, TaskRunnerFactory] = {}
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        self.last_recovery_count = 0

    def register_runner_factory(self, task_type: str, factory: TaskRunnerFactory) -> None:
        self._runner_factories[task_type] = factory

    def recover_after_restart(self) -> int:
        self.last_recovery_count = mark_incomplete_tasks_interrupted()
        return self.last_recovery_count

    def create(
        self,
        task_type: str,
        runner: TaskRunner,
        metadata: dict | None = None,
        request_payload: dict | None = None,
        retry_of: str = "",
    ) -> dict:
        task_id = str(uuid4())
        now = _now()
        record = {
            "task_id": task_id,
            "task_type": task_type,
            "status": "queued",
            "progress": 0,
            "message": "任务已创建，等待执行",
            "detail": "",
            "current_agent": "",
            "step_index": 0,
            "total_steps": 0,
            "created_at": now,
            "started_at": "",
            "completed_at": "",
            "updated_at": now,
            "elapsed_ms": 0,
            "step_timings": [],
            "result": None,
            "error": "",
            "cancel_requested": False,
            "events": [],
            "runner": runner,
            "metadata": metadata or {},
            "request_payload": request_payload or {},
            "retry_of": retry_of,
            "_started_monotonic": 0.0,
            "_active_steps": {},
        }
        with self._condition:
            self._tasks[task_id] = record
            self._append_event(record, "queued")
        thread = threading.Thread(target=self._execute, args=(task_id,), daemon=True)
        thread.start()
        return self.snapshot(task_id)

    def retry(self, task_id: str) -> dict:
        with self._lock:
            source = self._get(task_id)
            if source["status"] not in TERMINAL_STATUSES:
                raise ValueError("Only terminal tasks can be retried")
            runner = source.get("runner")
            if runner is None:
                factory = self._runner_factories.get(source["task_type"])
                if factory is None:
                    raise ValueError("This recovered task type does not support retry")
                runner = factory(copy(source.get("request_payload") or {}))
            metadata = copy(source["metadata"])
            metadata["retry_of"] = task_id
            request_payload = copy(source.get("request_payload") or {})
        return self.create(
            source["task_type"],
            runner,
            metadata,
            request_payload=request_payload,
            retry_of=task_id,
        )

    def cancel(self, task_id: str) -> dict:
        with self._condition:
            record = self._get(task_id)
            if record["status"] in TERMINAL_STATUSES:
                return self._snapshot(record)
            record["cancel_requested"] = True
            record["status"] = "cancelling"
            record["message"] = "正在停止任务"
            record["detail"] = "若模型请求正在进行，将在当前请求返回后停止后续 Agent。"
            record["updated_at"] = _now()
            self._append_event(record, "cancel_requested")
            return self._snapshot(record)

    def snapshot(self, task_id: str) -> dict:
        with self._lock:
            return self._snapshot(self._get(task_id))

    def events_since(self, task_id: str, cursor: int, timeout: float = 10) -> tuple[list[dict], str]:
        deadline = time.monotonic() + timeout
        with self._condition:
            record = self._get(task_id)
            while len(record["events"]) <= cursor and record["status"] not in TERMINAL_STATUSES:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._condition.wait(remaining)
            return list(record["events"][cursor:]), record["status"]

    def clear(self) -> None:
        with self._condition:
            self._tasks.clear()
            self._condition.notify_all()

    def _execute(self, task_id: str) -> None:
        with self._condition:
            record = self._get(task_id)
            record["status"] = "running"
            record["started_at"] = _now()
            record["_started_monotonic"] = time.monotonic()
            record["message"] = "任务开始执行"
            record["updated_at"] = _now()
            self._append_event(record, "started")

        def emit(event_type: str, **payload: Any) -> None:
            with self._condition:
                current = self._get(task_id)
                step_index = int(payload.get("step_index") or 0)
                if event_type == "agent_started" and step_index:
                    current["_active_steps"][step_index] = {
                        "started_at": _now(),
                        "started_monotonic": time.monotonic(),
                        "agent_name": payload.get("current_agent", ""),
                    }
                elif event_type == "agent_completed" and step_index:
                    started = current["_active_steps"].pop(step_index, None)
                    if started:
                        duration_ms = round(
                            (time.monotonic() - started["started_monotonic"]) * 1000
                        )
                        timing = {
                            "step_index": step_index,
                            "agent_name": payload.get("current_agent") or started["agent_name"],
                            "started_at": started["started_at"],
                            "completed_at": _now(),
                            "duration_ms": duration_ms,
                            "status": "completed",
                        }
                        current["step_timings"].append(timing)
                        payload["duration_ms"] = duration_ms
                for key in ("progress", "message", "detail", "current_agent", "step_index", "total_steps"):
                    if key in payload:
                        current[key] = payload[key]
                current["updated_at"] = _now()
                self._append_event(current, event_type, payload)

        def is_cancelled() -> bool:
            with self._lock:
                return bool(self._get(task_id)["cancel_requested"])

        try:
            result = record["runner"](emit, is_cancelled)
            if is_cancelled():
                raise TaskCancelled("Task cancelled by user")
            with self._condition:
                current = self._get(task_id)
                current.update(
                    status="completed",
                    progress=100,
                    message="任务处理完成",
                    detail="所有结果已生成并保存。",
                    result=result,
                    completed_at=_now(),
                    elapsed_ms=self._elapsed_ms(current),
                    updated_at=_now(),
                )
                self._append_event(current, "completed")
        except TaskCancelled:
            with self._condition:
                current = self._get(task_id)
                current.update(
                    status="cancelled",
                    message="任务已停止",
                    detail="已完成的只读检索不会被删除，未完成结果不会写入正式会话。",
                    completed_at=_now(),
                    elapsed_ms=self._elapsed_ms(current),
                    updated_at=_now(),
                )
                self._append_event(current, "cancelled")
        except Exception as exc:
            with self._condition:
                current = self._get(task_id)
                current.update(
                    status="failed",
                    message="任务执行失败",
                    detail="可以重试；模型调用异常时生成模块仍会优先自动回退模板模式。",
                    error=str(exc),
                    completed_at=_now(),
                    elapsed_ms=self._elapsed_ms(current),
                    updated_at=_now(),
                )
                self._append_event(current, "failed")

    def _append_event(self, record: dict, event_type: str, payload: dict | None = None) -> None:
        event = {
            "event_id": len(record["events"]),
            "event_type": event_type,
            "task_id": record["task_id"],
            "task_type": record["task_type"],
            "status": record["status"],
            "progress": record["progress"],
            "message": record["message"],
            "detail": record["detail"],
            "current_agent": record["current_agent"],
            "step_index": record["step_index"],
            "total_steps": record["total_steps"],
            "timestamp": _now(),
            "elapsed_ms": self._elapsed_ms(record),
            "step_timings": list(record["step_timings"]),
        }
        if payload:
            event.update(payload)
        record["events"].append(event)
        save_task_snapshot(self._persistence_payload(record))
        self._condition.notify_all()

    def _get(self, task_id: str) -> dict:
        if task_id not in self._tasks:
            persisted = load_task_snapshot(task_id)
            if persisted is None:
                raise KeyError(f"Unknown task_id: {task_id}")
            persisted.update(
                runner=None,
                cancel_requested=False,
                _started_monotonic=0.0,
                _active_steps={},
            )
            self._tasks[task_id] = persisted
        return self._tasks[task_id]

    def _persistence_payload(self, record: dict) -> dict:
        payload = {
            key: value
            for key, value in record.items()
            if key != "runner" and not key.startswith("_")
        }
        payload["elapsed_ms"] = self._elapsed_ms(record)
        return payload

    @staticmethod
    def _snapshot(record: dict) -> dict:
        return {
            key: value
            for key, value in record.items()
            if key not in {"runner", "events", "request_payload"} and not key.startswith("_")
        }

    @staticmethod
    def _elapsed_ms(record: dict) -> int:
        started = float(record.get("_started_monotonic") or 0)
        if started and record.get("status") not in TERMINAL_STATUSES:
            return round((time.monotonic() - started) * 1000)
        return int(record.get("elapsed_ms") or 0)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


task_manager = TaskManager()
