import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _context(**overrides) -> dict:
    payload = {
        "active_view": "report",
        "active_view_label": "学情报告",
        "domain": "tire",
        "profile_id": "undergrad_basic",
        "learner_type": "本科低年级学生",
        "learning_goal": "理解热氧老化与滑动磨损耦合机制",
        "diagnosis_score": 62,
        "diagnosis_level": "基础",
        "feedback_score": 100,
        "weak_points": ["热氧老化", "实验表征"],
        "strong_points": ["基础损伤分类"],
        "session_id": "demo-session",
        "recommended_action": "补充案例",
        "next_training_suggestion": "完成热氧老化形貌对比案例，再复核实验表征证据链。",
        "visible_summary": "报告已生成，下一步建议继续巩固。",
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("我当前的诊断得分是多少？", "62 分"),
        ("我当前的知识薄弱点是什么？", "热氧老化"),
        ("我的强项是什么？", "基础损伤分类"),
        ("我当前的学习目标是什么？", "理解热氧老化与滑动磨损耦合机制"),
        ("我现在的训练方向是什么？", "航空轮胎"),
    ],
)
def test_context_questions_use_fast_confirmed_state(question: str, expected: str):
    response = client.post("/api/assistant/ask", json={"question": question, "context": _context()})

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer_type"] == "context-summary"
    assert payload["generation_mode"] == "context-rules"
    assert payload["knowledge_source"] == "page-context"
    assert expected in payload["answer"]
    assert len(payload["agent_steps"]) == 2


def test_context_answer_does_not_invent_missing_score():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "我当前的诊断结果是什么？", "context": _context(diagnosis_score=None, diagnosis_level="")},
    )

    assert response.status_code == 200
    assert "尚未提交诊断" in response.json()["answer"]


def test_context_answer_combines_score_and_next_action():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "我现在多少分，下一步应该练什么？", "context": _context()},
    )

    assert response.status_code == 200
    answer = response.json()["answer"]
    assert "62 分" in answer
    assert "补充案例" in answer
    assert "热氧老化形貌对比案例" in answer


def test_context_answer_distinguishes_diagnosis_and_feedback_scores():
    response = client.post(
        "/api/assistant/ask",
        json={
            "question": "请告诉我诊断得分和刚才的反馈测试得分，下一步练什么？",
            "context": _context(recommended_action="进阶挑战"),
        },
    )

    assert response.status_code == 200
    answer = response.json()["answer"]
    assert "诊断得分为 62 分" in answer
    assert "反馈测试得分为 100 分" in answer
    assert "进阶挑战" in answer


@pytest.mark.parametrize("question", ["好", "问" * 801])
def test_assistant_rejects_invalid_question_length(question: str):
    response = client.post("/api/assistant/ask", json={"question": question, "context": _context()})

    assert response.status_code == 422


def test_domain_answer_returns_aligned_evidence_titles():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "热氧老化为什么会影响滑动磨损？", "context": _context(active_view="resources")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer_type"] == "domain-grounded"
    assert payload["evidence_ids"]
    assert len(payload["evidence_titles"]) == len(payload["evidence_ids"])


@pytest.mark.parametrize(
    ("question", "expected_keyword", "expected_view"),
    [
        ("报告咋导出？", "学情报告", "report"),
        ("我想恢复以前的训练记录", "历史训练会话", "history"),
        ("检索证据在哪看？", "知识证据库", "knowledge"),
        ("答完题后怎么提交反馈？", "反馈迭代", "feedback"),
    ],
)
def test_colloquial_interface_questions_use_fast_route(question: str, expected_keyword: str, expected_view: str):
    response = client.post("/api/assistant/ask", json={"question": question, "context": _context()})

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer_type"] == "interface-guide"
    assert payload["recommended_view"] == expected_view
    assert expected_keyword in payload["answer"]


@pytest.mark.parametrize(
    ("question", "expected_keyword"),
    [
        ("我这次哪里不会？", "热氧老化"),
        ("我擅长什么？", "基础损伤分类"),
        ("我接下来学什么？", "实验表征"),
    ],
)
def test_colloquial_context_questions_do_not_invoke_rag(question: str, expected_keyword: str):
    response = client.post("/api/assistant/ask", json={"question": question, "context": _context()})

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer_type"] == "context-summary"
    assert payload["generation_mode"] == "context-rules"
    assert expected_keyword in payload["answer"]


def test_pre_session_follow_up_uses_recent_messages_for_retrieval():
    context = _context(
        session_id=None,
        recent_messages=[
            {"role": "user", "content": "60 N、160 m 往复摩擦工况有哪些记录？"},
            {"role": "assistant", "content": "上一问聚焦 60 N、160 m 工况。"},
        ],
    )
    response = client.post(
        "/api/assistant/ask",
        json={"question": "沿用上一问，还应该补充哪些表征？", "context": context},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer_type"] == "domain-grounded"
    assert payload["evidence_ids"]
    assert len(payload["agent_steps"]) == 5


def test_review_rejection_question_uses_grounded_multi_agent_path():
    response = client.post(
        "/api/assistant/ask",
        json={
            "question": "为什么本轮动态回答被审核 Agent 驳回并重生？请引用当前会话中的风险点解释。",
            "context": _context(active_view="inquiry", active_view_label="智能训练工作台", session_id=None),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer_type"] == "domain-grounded"
    assert payload["evidence_ids"]
    assert len(payload["agent_steps"]) == 5


def test_feedback_follow_up_question_returns_confirmed_next_action():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "我已经完成反馈测试，现在应该先看什么？", "context": _context()},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer_type"] == "context-summary"
    assert "补充案例" in payload["answer"]
    assert "热氧老化形貌对比案例" in payload["answer"]
