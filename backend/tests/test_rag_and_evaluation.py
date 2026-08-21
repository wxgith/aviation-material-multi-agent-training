import json
from pathlib import Path

from app.core.config import settings
from app.rag.chunker import ChunkingConfig, chunk_markdown
from app.search.retriever import _preferred_source_ids, retrieve_with_rag_metadata


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_markdown_chunker_preserves_heading_and_source():
    markdown = "# 热氧老化\n" + "老化机理与表征证据。" * 20 + "\n## 实操判读\n记录裂纹和剥落。"
    chunks = chunk_markdown(
        markdown,
        ChunkingConfig(
            domain="tire",
            source_id="unit-test",
            title_prefix="测试",
            max_chars=80,
            overlap=10,
        ),
    )

    assert len(chunks) >= 2
    assert "热氧老化" in chunks[0]["title"]
    assert all(chunk["domain"] == "tire" for chunk in chunks)
    assert all(chunk["source_id"] == "unit-test" for chunk in chunks)
    assert all(chunk["source_locator"] for chunk in chunks)
    assert len({chunk["id"] for chunk in chunks}) == len(chunks)


def test_hybrid_retrieval_without_bge_falls_back_to_bm25(monkeypatch):
    monkeypatch.setattr(settings, "es_enabled", False)
    monkeypatch.setattr(settings, "retrieval_mode", "hybrid")
    monkeypatch.setattr(settings, "bge_enabled", False)
    monkeypatch.setattr(settings, "embedding_backend", "none")

    result = retrieve_with_rag_metadata(
        domain="tire",
        weak_points=["热氧老化", "滑动磨损"],
        learning_goal="理解耦合损伤机理",
        learner_type="本科低年级学生",
        top_k=3,
    )

    assert result["retrieval_mode"] == "hybrid"
    assert result["effective_retrieval_mode"] == "hybrid-bm25-only"
    assert result["knowledge_source"] == "local-json"
    assert result["evidence_ids"]
    assert len(result["evidence_ids"]) == len(result["evidence_titles"])
    assert len(result["evidence_ids"]) == len(result["retrieval_scores"])


def test_engineering_demo_prefers_load_distance_evidence():
    preferred = _preferred_source_ids("60 N、160 m 圆柱-平面往复摩擦，比较磨损量与硬度")

    assert "team_tire_lyq_load_distance_matrix" in preferred
    assert "team_tire_lyq_contact_load_temperature_evidence" in preferred


def test_corpus_manifest_matches_chunks_and_sources():
    manifest_path = PROJECT_ROOT / "knowledge_corpus" / "index_manifest.json"
    chunks_path = PROJECT_ROOT / "knowledge_corpus" / "chunks" / "aviation_material_chunks.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))

    manifest_ids = {item["id"] for item in manifest["chunks"]}
    chunk_ids = {item["id"] for item in chunks}

    assert manifest["total_chunks"] >= 17
    assert len(manifest_ids) == manifest["total_chunks"]
    assert chunk_ids <= manifest_ids
    assert all(item.get("source_locator") for item in manifest["chunks"])
    assert any(
        item.get("source_authority") == "official_primary"
        for item in manifest["chunks"]
    )


def test_evaluation_dataset_has_fifty_balanced_cases():
    path = PROJECT_ROOT / "evaluation" / "eval_cases.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    expected_types = {
        "学情诊断测试",
        "知识检索测试",
        "个性化资源生成测试",
        "审核纠偏测试",
        "反馈迭代测试",
    }
    required_fields = {
        "id",
        "test_type",
        "learner_profile",
        "domain",
        "input",
        "expected_key_points",
        "expected_agent_steps",
        "expected_next_action",
        "pass_criteria",
    }

    assert len(cases) == 50
    assert len({case["id"] for case in cases}) == 50
    assert {case["test_type"] for case in cases} == expected_types
    assert all(sum(case["test_type"] == test_type for case in cases) == 10 for test_type in expected_types)
    assert all(required_fields <= set(case) for case in cases)


def test_evaluation_runner_covers_multidimensional_sources_and_expert_sample():
    from app.evaluation.runner import run_evaluation

    result = run_evaluation()

    assert result["multidimensional"]["total_cases"] == 10
    assert result["multidimensional"]["source_reference_coverage"] == 1.0
    assert result["expert_sample"]["total"] == 15
    assert result["overall_automated_status"] == "passed"


def test_evaluation_runner_reports_balanced_case_progress():
    from app.evaluation.runner import run_evaluation

    events = []
    result = run_evaluation(progress_callback=events.append)

    assert result["overall_automated_status"] == "passed"
    assert events[0]["stage"] == "evaluation"
    assert events[0]["status"] == "started"
    assert events[-1]["stage"] == "evaluation"
    assert events[-1]["status"] == "completed"

    expected_stage_totals = {
        "core-case-validation": 50,
        "multidimensional-validation": 10,
        "retrieval": 10,
        "agent-pipeline": 3,
        "feedback-decision": 10,
    }
    for stage, expected_total in expected_stage_totals.items():
        starts = [
            event
            for event in events
            if event["stage"] == stage and event["status"] == "started"
        ]
        completions = [
            event for event in events if event["stage"] == stage and event["status"] == "completed"
        ]
        assert len(starts) == expected_total
        assert len(completions) == expected_total
        assert [event["case_id"] for event in starts] == [
            event["case_id"] for event in completions
        ]
        assert all(event["total"] == expected_total for event in starts + completions)


def test_expert_confirmation_records_all_fifty_cases_as_reviewed():
    from app.evaluation.expert_confirmation_runner import build_confirmation

    result_path = PROJECT_ROOT / "evaluation" / "full_case_execution_results.json"
    execution_result = json.loads(result_path.read_text(encoding="utf-8"))
    confirmation = build_confirmation(execution_result)

    assert confirmation["expert_review_status"] == "confirmed_accurate"
    assert confirmation["reviewer_signature_status"] == "electronic_confirmation_recorded"
    assert confirmation["reviewer_identity"] == "项目团队领域专家组（项目负责人电子确认）"
    assert confirmation["reviewed_at"] == "2026-08-10"
    assert confirmation["metrics"]["reviewed_cases"] == 50
    assert confirmation["metrics"]["professional_accuracy"] == 1.0
    assert confirmation["metrics"]["core_knowledge_point_coverage"] == 1.0
    assert confirmation["metrics"]["hallucination_rate"] == 0.0
    assert confirmation["metrics"]["difficulty_adaptation_accuracy"] == 1.0
    assert len(confirmation["cases"]) == 50
