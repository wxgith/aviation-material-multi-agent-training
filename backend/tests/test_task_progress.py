import time

from fastapi.testclient import TestClient

from app.main import app
from app.services.task_manager import TaskManager, TaskCancelled


client = TestClient(app)


def _wait_for_task(task_id: str, timeout: float = 10) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        payload = client.get(f"/api/tasks/{task_id}").json()
        if payload["status"] in {"completed", "failed", "cancelled"}:
            return payload
        time.sleep(0.02)
    raise AssertionError("task did not finish")


def _agent_payload() -> dict:
    profile = client.get("/api/profiles").json()[0]
    questions = client.get("/api/questions", params={"domain": "tire"}).json()
    answers = [
        {"question_id": item["id"], "answer": item["answer"]}
        for item in questions
    ]
    diagnosis = client.post(
        "/api/diagnosis",
        json={
            "profile_id": profile["profile_id"],
            "profile_override": profile,
            "domain": "tire",
            "answers": answers,
        },
    ).json()
    return {
        "profile_id": profile["profile_id"],
        "profile_override": profile,
        "domain": "tire",
        "diagnosis_result": diagnosis,
        "learning_goal": profile["default_goal"],
    }


def test_agent_task_reports_real_agent_progress_and_result():
    response = client.post("/api/agent/tasks", json=_agent_payload())
    assert response.status_code == 200
    completed = _wait_for_task(response.json()["task_id"])

    assert completed["status"] == "completed"
    assert completed["progress"] == 100
    assert completed["elapsed_ms"] >= 0
    assert len(completed["step_timings"]) == 6
    assert all(item["duration_ms"] >= 0 for item in completed["step_timings"])
    assert len(completed["result"]["agent_steps"]) == 6
    event_stream = client.get(f"/api/tasks/{response.json()['task_id']}/events")
    assert event_stream.status_code == 200
    assert "event: progress" in event_stream.text
    assert "agent_started" in event_stream.text
    assert "agent_completed" in event_stream.text
    assert "step_timings" in event_stream.text


def test_task_manager_supports_cooperative_cancel_and_retry():
    manager = TaskManager()

    def runner(emit, cancelled):
        for index in range(30):
            if cancelled():
                raise TaskCancelled()
            emit("working", progress=index, message="working")
            time.sleep(0.005)
        return {"ok": True}

    task = manager.create("test", runner)
    manager.cancel(task["task_id"])
    deadline = time.monotonic() + 2
    while manager.snapshot(task["task_id"])["status"] not in {"cancelled", "failed"}:
        assert time.monotonic() < deadline
        time.sleep(0.01)
    assert manager.snapshot(task["task_id"])["status"] == "cancelled"

    retried = manager.retry(task["task_id"])
    while manager.snapshot(retried["task_id"])["status"] not in {"completed", "failed"}:
        assert time.monotonic() < deadline
        time.sleep(0.01)
    assert manager.snapshot(retried["task_id"])["status"] == "completed"


def test_completed_session_can_be_listed_and_restored():
    created = client.post("/api/agent/tasks", json=_agent_payload()).json()
    completed = _wait_for_task(created["task_id"])
    session_id = completed["result"]["session_id"]

    listing = client.get("/api/sessions").json()
    restored = client.get(f"/api/sessions/{session_id}")

    assert any(item["session_id"] == session_id for item in listing["items"])
    assert restored.status_code == 200
    assert restored.json()["session_id"] == session_id
    assert len(restored.json()["agent_steps"]) == 6
