import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.evidence.catalog import (
    catalog_status,
    condition_match_strategy,
    get_asset,
    parse_condition_query,
    resolve_assets,
)
from app.evaluation.batch2_runner import validate_batch2_dataset
from app.main import app
from app.search.retriever import retrieve_with_rag_metadata


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = PROJECT_ROOT / "knowledge_corpus" / "experimental_assets" / "catalog.json"
EVAL_PATH = PROJECT_ROOT / "evaluation" / "team_experiment_eval_cases.json"
BATCH2_EVAL_PATH = PROJECT_ROOT / "evaluation" / "team_experiment_eval_cases_batch2.json"
client = TestClient(app)


def test_experimental_catalog_contains_four_reviewed_topics_and_media():
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    counts = {item["topic"]: item["asset_count"] for item in payload["topics"]}

    assert counts == {
        "service_tire_wear": 10,
        "thermal_aging_multimodal": 15,
        "uv_aging_wear_morphology": 12,
        "load_distance_morphology_matrix": 16,
    }
    assert catalog_status()["asset_count"] == 53
    for asset in payload["assets"]:
        assert asset["review_status"] in {"reviewed", "approved"}
        assert asset["authorization_status"] == "authorized"
        assert len(asset["source_sha256"]) == 64
        assert (CATALOG_PATH.parent / asset["media_path"]).is_file()


def test_evidence_resolver_and_media_api_are_traceable():
    assets = resolve_assets(
        evidence_ids=["team_tire_rxq_aging_multimodal_evidence-c002-example"],
        limit=4,
    )
    assert len(assets) == 4
    assert {item["topic"] for item in assets} == {"thermal_aging_multimodal"}

    asset_id = assets[0]["asset_id"]
    detail = client.get(f"/api/evidence/assets/{asset_id}")
    media = client.get(f"/api/evidence/assets/{asset_id}/media")
    assert detail.status_code == 200
    assert detail.json()["source_reference"].startswith("授权团队实验资料/")
    assert media.status_code == 200
    assert media.headers["content-type"].startswith("image/")
    assert get_asset(asset_id)["limitations"]


def test_team_experiment_evaluation_cases_reference_known_assets():
    payload = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    known_assets = {
        item["asset_id"]
        for item in json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["assets"]
    }
    assert len(payload["cases"]) == 20
    for case in payload["cases"]:
        assert len(case["expected_agent_steps"]) == 6
        assert set(case.get("expected_asset_ids", [])).issubset(known_assets)


def test_batch2_evaluation_and_condition_matrix_are_complete():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    known_assets = {item["asset_id"] for item in catalog["assets"]}
    payload = json.loads(BATCH2_EVAL_PATH.read_text(encoding="utf-8"))
    matrix_assets = [
        item
        for item in catalog["assets"]
        if item["topic"] == "load_distance_morphology_matrix"
        and item["modality"] == "optical_image"
    ]
    uv_assets = [item for item in catalog["assets"] if item["topic"] == "uv_aging_wear_morphology"]

    assert len(payload["cases"]) == 20
    assert len(matrix_assets) == 15
    assert {(item["condition"]["normal_load_N"], item["condition"]["sliding_distance_m"]) for item in matrix_assets} == {
        (load, distance) for load in (40, 50, 60) for distance in (20, 40, 80, 120, 160)
    }
    assert {item["condition"]["aging_duration_h"] for item in uv_assets} == {24, 504, 576}
    for case in payload["cases"]:
        assert len(case["expected_agent_steps"]) == 6
        assert set(case["expected_asset_ids"]).issubset(known_assets)


def test_batch2_asset_ranking_uses_duration_load_and_distance():
    uv = resolve_assets(
        source_ids=["team_tire_rxq_uv_wear_morphology"],
        query_text="504 h 摩擦前与摩擦后形貌",
        limit=4,
    )
    matrix = resolve_assets(
        source_ids=["team_tire_lyq_load_distance_matrix"],
        query_text="60 N、160 m光学形貌",
        limit=4,
    )

    assert uv[0]["asset_id"] == "RXQ-UV-H0504-IMG-01"
    assert all(item["condition"]["aging_duration_h"] == 504 for item in uv)
    assert matrix[0]["asset_id"] == "LYQ-LOAD-L60-D160-OPT-01"


def test_condition_parser_supports_chinese_lists_and_ranges():
    load_comparison = parse_condition_query("比较80米时40、50、60 N磨损")
    distance_range = parse_condition_query("检索40 N下20到160米往复摩擦矩阵")
    uv_comparison = parse_condition_query("比较24、504、576小时紫外老化后表面形貌")

    assert load_comparison["normal_load_N"] == [40.0, 50.0, 60.0]
    assert load_comparison["sliding_distance_m"] == [80.0]
    assert distance_range["normal_load_N"] == [40.0]
    assert distance_range["sliding_distance_m"] == [20.0, 160.0]
    assert distance_range["range_or_sequence"] is True
    assert uv_comparison["aging_duration_h"] == [24.0, 504.0, 576.0]
    assert condition_match_strategy(load_comparison) == "exact-condition-group"


def test_load_distance_group_retrieval_returns_complete_fixed_load_series():
    assets = resolve_assets(
        source_ids=["team_tire_lyq_load_distance_matrix"],
        query_text="检索40 N下20到160米往复摩擦矩阵",
        limit=8,
    )
    image_assets = [item for item in assets if item["modality"] == "optical_image"]

    assert [item["condition"]["sliding_distance_m"] for item in image_assets] == [
        20,
        40,
        80,
        120,
        160,
    ]
    assert {item["condition"]["normal_load_N"] for item in image_assets} == {40}
    assert "LYQ-LOAD-MATRIX-TREND-01" in {item["asset_id"] for item in assets}


def test_load_distance_group_retrieval_returns_all_loads_at_fixed_distance():
    assets = resolve_assets(
        source_ids=["team_tire_lyq_load_distance_matrix"],
        query_text="比较80米时40、50、60 N磨损",
        limit=8,
    )
    image_assets = [item for item in assets if item["modality"] == "optical_image"]

    assert [item["condition"]["normal_load_N"] for item in image_assets] == [40, 50, 60]
    assert {item["condition"]["sliding_distance_m"] for item in image_assets} == {80}


def test_load_distance_progression_without_explicit_endpoints_returns_full_series():
    assets = resolve_assets(
        source_ids=["team_tire_lyq_load_distance_matrix"],
        query_text="分析60 N下距离增加时磨损和硬度变化",
        limit=8,
    )
    image_ids = [item["asset_id"] for item in assets if item["modality"] == "optical_image"]

    assert image_ids[0] == "LYQ-LOAD-L60-D020-OPT-01"
    assert image_ids[-1] == "LYQ-LOAD-L60-D160-OPT-01"
    assert len(image_ids) == 5


def test_uv_cross_duration_and_same_duration_comparisons_are_complete():
    cross_duration = resolve_assets(
        source_ids=["team_tire_rxq_uv_wear_morphology"],
        query_text="比较24、504、576小时紫外老化后表面形貌",
        limit=8,
    )
    before_after = resolve_assets(
        source_ids=["team_tire_rxq_uv_wear_morphology"],
        query_text="比较504小时紫外老化的摩擦前与摩擦后表面",
        limit=8,
    )

    assert [item["condition"]["aging_duration_h"] for item in cross_duration] == [
        24,
        504,
        576,
    ]
    assert {item["asset_id"] for item in cross_duration} == {
        "RXQ-UV-H0024-IMG-01",
        "RXQ-UV-H0504-IMG-02",
        "RXQ-UV-H0576-IMG-01",
    }
    assert {
        "RXQ-UV-H0504-IMG-01",
        "RXQ-UV-H0504-IMG-02",
    }.issubset({item["asset_id"] for item in before_after})


def test_conceptual_matrix_and_uv_brightness_queries_keep_summary_evidence():
    matrix = resolve_assets(
        query_text="载荷距离矩阵的磨损量和硬度趋势",
        limit=8,
    )
    brightness = resolve_assets(
        query_text="学习者把图像亮度直接当作老化程度，需要同尺度比较",
        limit=8,
    )

    assert matrix[0]["asset_id"] == "LYQ-LOAD-MATRIX-TREND-01"
    assert {
        "RXQ-UV-H0024-IMG-01",
        "RXQ-UV-H0504-IMG-02",
    }.issubset({item["asset_id"] for item in brightness})


def test_json_fallback_prioritizes_condition_bound_experiment_chunks(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "retrieval_mode", "bm25")
    result = retrieve_with_rag_metadata(
        domain="tire",
        weak_points=["载荷", "滑动距离"],
        learning_goal="检索60 N、160 m往复摩擦的工况和形貌",
        learner_type="本科低年级学生",
        top_k=5,
    )

    assert result["knowledge_source"] == "local-json"
    assets = resolve_assets(
        evidence_ids=result["evidence_ids"],
        source_ids=[
            chunk.get("source_id", "")
            for chunk in result["chunks"]
            if chunk.get("source_id")
        ],
        query_text="检索60 N、160 m往复摩擦的工况和形貌",
        limit=8,
    )
    assert assets[0]["asset_id"] == "LYQ-LOAD-L60-D160-OPT-01"
    assert "LYQ-LOAD-MATRIX-TREND-01" in {item["asset_id"] for item in assets}


def test_batch2_dataset_validator_accepts_current_catalog():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    cases = json.loads(BATCH2_EVAL_PATH.read_text(encoding="utf-8"))["cases"]
    assets = {item["asset_id"]: item for item in catalog["assets"]}

    result = validate_batch2_dataset(cases, assets)

    assert result["passed"] is True
    assert result["total_cases"] == 20
    assert result["missing_asset_references"] == {}
