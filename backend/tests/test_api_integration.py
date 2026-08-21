from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.database import reset_engine_cache
from app.main import app
from app.services.session_store import session_store


client = TestClient(app)


def _answers(domain: str, correct: bool = True) -> list[dict]:
    questions = client.get("/api/questions", params={"domain": domain}).json()
    return [
        {
            "question_id": question["id"],
            "answer": question["answer"] if correct else "__wrong__",
        }
        for question in questions
    ]


def _run_session(profile_override: dict | None = None) -> tuple[str, dict]:
    profile = client.get("/api/profiles").json()[0]
    if profile_override:
        profile.update(profile_override)
    diagnosis_response = client.post(
        "/api/diagnosis",
        json={
            "profile_id": profile["profile_id"],
            "profile_override": profile,
            "domain": "tire",
            "answers": _answers("tire", correct=False),
        },
    )
    assert diagnosis_response.status_code == 200
    diagnosis = diagnosis_response.json()
    run_response = client.post(
        "/api/agent/run",
        json={
            "profile_id": profile["profile_id"],
            "profile_override": profile,
            "domain": "tire",
            "diagnosis_result": diagnosis,
            "learning_goal": profile["default_goal"],
        },
    )
    assert run_response.status_code == 200
    payload = run_response.json()
    return payload["session_id"], payload


def test_profile_override_and_feedback_regeneration_complete_the_api_loop():
    session_id, run_payload = _run_session(
        {"learner_type": "自定义科研训练学员", "background": "用户编辑后的背景"}
    )
    assert len(run_payload["agent_steps"]) == 6

    report = client.get(f"/api/sessions/{session_id}/report")
    assert report.status_code == 200
    assert report.json()["profile"]["background"] == "用户编辑后的背景"

    feedback = client.post(
        f"/api/sessions/{session_id}/feedback",
        json={"answers": [], "self_feedback": "希望用更直观的案例重新解释"},
    )
    assert feedback.status_code == 200
    feedback_payload = feedback.json()
    assert feedback_payload["next_action"] == "降维解释"
    assert len(feedback_payload["iteration_agent_steps"]) == 4
    assert feedback_payload["updated_resources"]["personalized_lecture"]["difficulty"] == "降维入门"


def test_knowledge_source_catalog_api_returns_manifest_statistics():
    response = client.get("/api/knowledge/sources", params={"domain": "tire"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["source_count"] >= 1
    assert payload["summary"]["manifest_total_chunks"] >= 1439
    assert all(source["domain"] == "tire" for source in payload["sources"])


def test_literature_experiment_api_distinguishes_published_evidence():
    response = client.get("/api/knowledge/experiments", params={"domain": "brake"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["evidence_type"] == "published_literature_experiment"
    assert payload["reviewed_count"] == 1
    assert payload["review_status"] == "expert_reviewed"
    assert payload["records"][0]["source_id"] == "brake_nasa_tn_d_8006"


def test_evaluation_summary_exposes_execution_and_expert_review_metrics():
    response = client.get("/api/evaluation/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "passed"
    assert payload["core_cases"] == {"total": 50, "passed": 50, "pass_rate": 1.0}
    assert payload["machine_assisted_metrics"]["correction_cases"] == 8
    assert payload["expert_review"]["confirmed"] is True
    assert payload["expert_review"]["professional_accuracy"] == 1.0
    assert payload["expert_review"]["hallucination_rate"] == 0.0
    assert payload["expert_review"]["signature_status"] == "electronic_confirmation_recorded"


def test_sql_session_can_be_recovered_after_memory_store_is_cleared(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(settings, "database_enabled", True)
    monkeypatch.setattr(settings, "data_backend", "sql")
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'recovery.db'}")
    reset_engine_cache()

    session_id, _ = _run_session()
    feedback = client.post(
        f"/api/sessions/{session_id}/feedback",
        json={"answers": [], "self_feedback": "需要更直观的证据对比"},
    )
    assert feedback.status_code == 200
    session_store.clear()

    resources = client.get(f"/api/sessions/{session_id}/resources")
    report = client.get(f"/api/sessions/{session_id}/report")
    assert resources.status_code == 200
    assert resources.json()["personalized_lecture"]
    assert report.status_code == 200
    assert report.json()["session_id"] == session_id
    assert report.json()["recommended_action"] == "降维解释"
    assert report.json()["feedback_history"][0]["feedback_score"] == 0
    exported = client.get(f"/api/sessions/{session_id}/export")
    assert "## 14. 反馈迭代记录" in exported.text
    assert "需要更直观的证据对比" in exported.text
