import time

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _context(**overrides) -> dict:
    context = {
        "active_view": "home",
        "active_view_label": "首页",
        "domain": "tire",
        "profile_id": "undergrad_basic",
        "learner_type": "本科低年级学生",
        "learning_goal": "理解航空轮胎热氧老化与滑动磨损。",
        "visible_summary": "首页显示 SQL、Elasticsearch、LLM 和知识资产状态。",
    }
    context.update(overrides)
    return context


def test_interface_assistant_answers_navigation_question_immediately():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "我第一次使用应该从哪里开始？", "context": _context()},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer_type"] == "interface-guide"
    assert payload["generation_mode"] == "ui-guide-rules"
    assert payload["recommended_view"] == "diagnosis"
    assert len(payload["agent_steps"]) == 2
    assert "加载演示案例" in payload["answer"]


def test_interface_assistant_runs_grounded_loop_without_session():
    response = client.post(
        "/api/assistant/ask",
        json={
            "question": "热氧老化为什么会影响后续滑动磨损表现？",
            "context": _context(active_view="diagnosis", active_view_label="学情诊断"),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer_type"] == "domain-grounded"
    assert payload["generation_mode"] == "mock-template"
    assert payload["evidence_ids"]
    assert len(payload["agent_steps"]) == 5
    assert payload["knowledge_source"] == "local-json"


def test_interface_assistant_task_reports_progress_and_completes():
    started = client.post(
        "/api/assistant/tasks",
        json={"question": "当前页面有什么作用？", "context": _context(active_view="report", active_view_label="学情报告")},
    )
    assert started.status_code == 200
    task_id = started.json()["task_id"]

    snapshot = started.json()
    deadline = time.time() + 3
    while snapshot["status"] not in {"completed", "failed", "cancelled"} and time.time() < deadline:
        time.sleep(0.02)
        snapshot = client.get(f"/api/tasks/{task_id}").json()

    assert snapshot["status"] == "completed"
    assert snapshot["result"]["answer_type"] == "interface-guide"
    assert snapshot["progress"] == 100
