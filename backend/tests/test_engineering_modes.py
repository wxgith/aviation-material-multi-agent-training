from pathlib import Path

import pytest

from app.agents.orchestrator import orchestrator
from app.core.config import settings
from app.db.database import _connect_args, reset_engine_cache, session_scope
from app.db.models import DiagnosisRecordORM
from app.llm.client import (
    _measurement_tokens,
    _validate_generated_resources,
    maybe_generate_resources_with_llm,
)
from app.models.schemas import AgentRunRequest, AnswerSubmission
from app.search.retriever import _preferred_source_boost, retrieve_with_optional_es
from app.services.data_loader import get_profile, get_questions_by_domain
from app.services.diagnosis_service import evaluate_diagnosis
from app.services.resource_service import generate_resources


def _demo_diagnosis():
    questions = get_questions_by_domain("tire")
    answers = [
        AnswerSubmission(question_id=question["id"], answer=question["answer"])
        for question in questions
    ]
    return evaluate_diagnosis("undergrad_basic", "tire", answers)


def test_database_enabled_writes_diagnosis_record(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(settings, "database_enabled", True)
    monkeypatch.setattr(settings, "data_backend", "sql")
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'agents_test.db'}")
    reset_engine_cache()

    profile = get_profile("undergrad_basic")
    diagnosis = _demo_diagnosis()
    session = orchestrator.run(
        AgentRunRequest(
            profile_id="undergrad_basic",
            domain="tire",
            diagnosis_result=diagnosis,
            learning_goal=profile["default_goal"],
        )
    )

    with session_scope() as db:
        count = (
            db.query(DiagnosisRecordORM)
            .filter(DiagnosisRecordORM.session_id == session["session_id"])
            .count()
        )
    assert count == 1

    monkeypatch.setattr(settings, "database_enabled", False)
    monkeypatch.setattr(settings, "data_backend", "json")
    reset_engine_cache()


def test_database_connect_timeout_is_bounded(monkeypatch):
    monkeypatch.setattr(
        settings,
        "database_url",
        "mysql+pymysql://user:password@127.0.0.1:3306/agents",
    )

    assert _connect_args()["connect_timeout"] == 3


def test_es_disabled_uses_local_json_retrieval(monkeypatch):
    monkeypatch.setattr(settings, "es_enabled", False)
    chunks, source = retrieve_with_optional_es(
        domain="tire",
        weak_points=["热氧老化"],
        learning_goal="理解热氧老化",
        learner_type="本科低年级学生",
        top_k=2,
    )

    assert source == "local-json"
    assert chunks


def test_es_enabled_prefers_es_when_available(monkeypatch):
    fake_chunk = {
        "id": "es-k01",
        "domain": "tire",
        "title": "ES 检索片段",
        "tags": ["热氧老化"],
        "content": "来自 Elasticsearch 的测试片段",
        "source_type": "es_test",
    }
    monkeypatch.setattr(settings, "es_enabled", True)
    monkeypatch.setattr("app.search.retriever.es_connected", lambda: True)
    monkeypatch.setattr("app.search.retriever._retrieve_from_es", lambda *args, **kwargs: [fake_chunk])

    chunks, source = retrieve_with_optional_es(
        domain="tire",
        weak_points=["热氧老化"],
        learning_goal="理解热氧老化",
        learner_type="本科低年级学生",
        top_k=2,
    )

    assert source == "elasticsearch"
    assert chunks[0]["id"] == "es-k01"
    monkeypatch.setattr(settings, "es_enabled", False)


def test_preferred_es_source_boost_never_becomes_negative():
    assert all(_preferred_source_boost(index) > 0 for index in range(10))


def test_llm_disabled_uses_mock_generation(monkeypatch):
    monkeypatch.setattr(settings, "llm_enabled", False)
    profile = get_profile("undergrad_basic")
    diagnosis = _demo_diagnosis()
    resources = generate_resources(
        profile=profile,
        domain="tire",
        diagnosis=diagnosis,
        retrieved_chunks=[],
        learning_goal=profile["default_goal"],
    )

    assert resources["generation_mode"] == "mock-template"


def test_llm_enabled_stable_mode_skips_whole_resource_generation(monkeypatch):
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "llm_resource_generation_enabled", False)
    monkeypatch.setattr(
        "app.llm.client.llm_client.chat_json",
        lambda *args, **kwargs: pytest.fail("stable mode must not call the resource LLM"),
    )
    base_resources = {
        "personalized_lecture": {"sections": [{"heading": "基础", "content": "模板"}]},
        "practical_guide": {"steps": ["记录工况"]},
        "graded_quiz": [{"question": "测试"}],
        "case_task": {"brief": "案例"},
        "difficulty_match": {"resource_difficulty": "降维入门"},
    }

    resources = maybe_generate_resources_with_llm(
        profile=get_profile("undergrad_basic"),
        domain="tire",
        diagnosis=_demo_diagnosis(),
        retrieved_chunks=[],
        learning_goal="test",
        base_resources=base_resources,
    )

    assert resources["generation_mode"] == "mock-template-stable"
    assert resources["generation_audit"]["outcome"] == "disabled"
    assert resources["personalized_lecture"] == base_resources["personalized_lecture"]


def test_llm_error_falls_back_to_mock(monkeypatch):
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "llm_resource_generation_enabled", True)
    monkeypatch.setattr(settings, "llm_base_url", "http://127.0.0.1:1/v1")
    monkeypatch.setattr(settings, "llm_api_key", "test")
    monkeypatch.setattr(settings, "llm_model", "test-model")
    base_resources = {
        "personalized_lecture": {},
        "practical_guide": {},
        "graded_quiz": [],
        "case_task": {},
        "difficulty_match": {},
    }

    resources = maybe_generate_resources_with_llm(
        profile=get_profile("undergrad_basic"),
        domain="tire",
        diagnosis=_demo_diagnosis(),
        retrieved_chunks=[],
        learning_goal="test",
        base_resources=base_resources,
    )

    assert resources["generation_mode"] == "mock-template-fallback"
    assert "llm_error" in resources
    monkeypatch.setattr(settings, "llm_enabled", False)


def test_resource_validation_rejects_implicit_conditions_and_unbound_values():
    chunks = [
        {
            "id": "evidence-1",
            "content": "60 N、160 m 工况记录磨损量 0.1605 g，硬度 46.5714 HA。",
        }
    ]
    resources = {
        "personalized_lecture": {
            "sections": [
                {
                    "heading": "工况分析",
                    "content": "温度未显式列出但隐含在试验边界中，界面温度为 80 °C。",
                    "evidence_ids": ["evidence-1"],
                }
            ]
        },
        "practical_guide": {
            "steps": ["记录载荷和距离。"],
            "constraints": ["缺失参数保持未知。"],
            "evidence_ids": ["evidence-1"],
        },
        "graded_quiz": [
            {"explanation": "有解析"},
            {"explanation": "有解析"},
            {"explanation": "有解析"},
        ],
        "case_task": {"brief": "完成证据记录。", "evidence_ids": ["evidence-1"]},
        "difficulty_match": {},
    }

    with pytest.raises(ValueError, match="隐含或可推定条件"):
        _validate_generated_resources(resources, chunks)


def test_resource_validation_accepts_values_found_in_bound_evidence():
    chunks = [
        {
            "id": "evidence-1",
            "content": "60 N、160 m 工况记录磨损量 0.1605 g，硬度 46.5714 HA。",
        }
    ]
    resources = {
        "personalized_lecture": {
            "sections": [
                {
                    "heading": "精确工况",
                    "content": "证据记录为 60 N、160 m、0.1605 g 和 46.5714 HA；机理仍待验证。",
                    "evidence_ids": ["evidence-1"],
                }
            ]
        },
        "practical_guide": {
            "steps": ["记录证据中的工况。"],
            "constraints": ["缺失参数保持未知。"],
            "evidence_ids": ["evidence-1"],
        },
        "graded_quiz": [
            {"explanation": "有解析"},
            {"explanation": "有解析"},
            {"explanation": "有解析"},
        ],
        "case_task": {"brief": "完成证据记录。", "evidence_ids": ["evidence-1"]},
        "difficulty_match": {},
    }

    _validate_generated_resources(resources, chunks)


def test_measurement_tokens_inherit_units_from_markdown_table_headers():
    evidence = (
        "| 老化/d | 样品 | 界面温度/°C | 质量损失/mg | 硬度变化/HA |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 7 | 3 | 73.40564 | 32.6000 | 12.7200 |"
    )

    tokens = _measurement_tokens(evidence)

    assert "7d" in tokens
    assert "73.40564°c" in tokens
    assert "32.6000mg" in tokens
    assert "12.7200ha" in tokens
