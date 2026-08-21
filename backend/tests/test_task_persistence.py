import time

from sqlalchemy import create_engine, text

from app.core.config import settings
from app.db.database import reset_engine_cache
from app.db.task_repository import save_task_snapshot
from app.services.task_manager import TaskManager


def _enable_sqlite(monkeypatch, tmp_path):
    database_path = tmp_path / "tasks.db"
    url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setattr(settings, "database_enabled", True)
    monkeypatch.setattr(settings, "data_backend", "sql")
    monkeypatch.setattr(settings, "database_url", url)
    reset_engine_cache()
    return url


def _wait(manager: TaskManager, task_id: str, terminal=None) -> dict:
    terminal = terminal or {"completed", "failed", "cancelled", "interrupted"}
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        snapshot = manager.snapshot(task_id)
        if snapshot["status"] in terminal:
            return snapshot
        time.sleep(0.01)
    raise AssertionError("task did not reach a terminal state")


def test_completed_task_can_be_recovered_from_sql(monkeypatch, tmp_path):
    url = _enable_sqlite(monkeypatch, tmp_path)
    manager = TaskManager()

    def runner(emit, _cancelled):
        emit("agent_started", progress=20, current_agent="test-agent", step_index=1, total_steps=1)
        emit("agent_completed", progress=90, current_agent="test-agent", step_index=1, total_steps=1)
        return {"answer": "persisted"}

    created = manager.create("test_task", runner, request_payload={"value": 7})
    completed = _wait(manager, created["task_id"])
    recovered = TaskManager().snapshot(created["task_id"])

    assert completed["status"] == "completed"
    assert recovered["status"] == "completed"
    assert recovered["result"] == {"answer": "persisted"}
    assert len(recovered["step_timings"]) == 1
    with create_engine(url).connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM async_tasks")).scalar() == 1


def test_running_task_becomes_interrupted_and_can_retry_original_request(monkeypatch, tmp_path):
    _enable_sqlite(monkeypatch, tmp_path)
    now = "2026-08-12T10:00:00+00:00"
    assert save_task_snapshot(
        {
            "task_id": "restart-task",
            "task_type": "recoverable",
            "status": "running",
            "progress": 42,
            "message": "running",
            "detail": "step two",
            "current_agent": "retrieval-agent",
            "step_index": 2,
            "total_steps": 6,
            "created_at": now,
            "started_at": now,
            "updated_at": now,
            "elapsed_ms": 1200,
            "step_timings": [],
            "metadata": {"domain": "tire"},
            "request_payload": {"question": "retry me"},
            "events": [],
        }
    )

    manager = TaskManager()
    manager.register_runner_factory(
        "recoverable",
        lambda payload: lambda _emit, _cancelled: {"question": payload["question"], "retried": True},
    )
    assert manager.recover_after_restart() == 1
    interrupted = manager.snapshot("restart-task")
    retried = manager.retry("restart-task")
    completed = _wait(manager, retried["task_id"])

    assert interrupted["status"] == "interrupted"
    assert interrupted["progress"] == 42
    assert completed["status"] == "completed"
    assert completed["result"] == {"question": "retry me", "retried": True}
    assert completed["metadata"]["retry_of"] == "restart-task"
