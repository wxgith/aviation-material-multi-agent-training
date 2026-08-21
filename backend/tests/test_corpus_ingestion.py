import json
from pathlib import Path

from app.rag.chunker import ChunkingConfig, chunk_markdown
from app.rag.structured_parser import jats_xml_to_markdown, zenodo_json_to_markdown
from app.search.retriever import _diversify_by_source, _expand_query_terms, _preferred_source_ids
from app.services.corpus_service import build_source_catalog
from app.services.literature_evidence_service import list_literature_experiments


def test_english_domain_terms_are_mapped_to_chinese_training_tags():
    chunks = chunk_markdown(
        "# Experiment\nAircraft tire fatigue wear was measured at several slip angles.",
        ChunkingConfig(domain="tire", source_id="paper", title_prefix="Paper"),
    )

    assert {"滑动磨损", "疲劳磨损", "实验表征"} <= set(chunks[0]["tags"])


def test_jats_and_zenodo_sources_can_be_parsed(tmp_path: Path):
    source = {
        "source_id": "unit-source",
        "domain": "composite",
        "title": "Unit source",
        "url": "https://example.test/source",
        "license_or_authorization": "CC BY 4.0",
        "standard_number": "10.0000/example",
        "document_type": "open_dataset_metadata",
    }
    xml_path = tmp_path / "article.xml"
    xml_path.write_text(
        "<article><front><article-meta><title-group><article-title>Impact study"
        "</article-title></title-group><abstract><p>Abstract text.</p></abstract>"
        "</article-meta></front><body><sec id='s1'><title>Methods</title>"
        "<p>C-scan experiment.</p></sec></body></article>",
        encoding="utf-8",
    )
    markdown, sections = jats_xml_to_markdown(xml_path, source)
    assert sections == 1
    assert "# Impact study" in markdown
    assert "## Methods [s1]" in markdown
    assert "source_sha256:" in markdown

    json_path = tmp_path / "record.json"
    json_path.write_text(
        '{"metadata":{"title":"C-scan data","description":"<p>Impact data</p>",'
        '"doi":"10.0000/example","license":{"id":"cc-by-4.0"},'
        '"resource_type":{"title":"Dataset"}},"files":[]}',
        encoding="utf-8",
    )
    dataset_markdown, dataset_sections = zenodo_json_to_markdown(json_path, source)
    assert dataset_sections == 4
    assert "Impact data" in dataset_markdown
    assert "cc-by-4.0" in dataset_markdown


def test_chinese_query_expansion_adds_english_source_terms():
    query = _expand_query_terms(
        ["无损检测图像判读", "分层"],
        "判读复合材料冲击损伤",
        "材料方向研究生",
    )

    assert "C-scan" in query
    assert "delamination" in query
    assert "impact damage" in query


def test_retrieval_evidence_is_diversified_by_document_source():
    chunks = [
        {"id": f"paper-a-{index}", "source_id": "paper-a", "_score": 10 - index}
        for index in range(5)
    ] + [
        {"id": "manual-1", "source_id": "manual", "_score": 4},
        {"id": "case-1", "source_id": "case", "_score": 3},
        {"id": "standard-1", "source_id": "standard", "_score": 2},
    ]

    selected = _diversify_by_source(chunks, top_k=5, max_per_source=2)

    assert [item["source_id"] for item in selected].count("paper-a") == 2
    assert {item["source_id"] for item in selected} == {
        "paper-a",
        "manual",
        "case",
        "standard",
    }


def test_multidimensional_evaluation_cases_cover_traceable_sources():
    path = Path(__file__).resolve().parents[2] / "evaluation" / "eval_cases_multidimensional.json"
    cases = json.loads(path.read_text(encoding="utf-8"))

    assert len(cases) == 10
    assert len({case["id"] for case in cases}) == 10
    assert {case["domain"] for case in cases} == {"tire", "brake", "composite"}
    assert all(case["expected_evidence_sources"] for case in cases)
    assert all(case["expected_agent_steps"] == 6 for case in cases)


def test_source_catalog_exposes_traceable_ingestion_status():
    catalog = build_source_catalog(domain="composite", query="impact")

    assert catalog["summary"]["source_count"] >= 1
    assert catalog["summary"]["manifest_total_chunks"] >= 1439
    assert all(source["domain"] == "composite" for source in catalog["sources"])
    assert any(source["source_id"] == "composite_pmc_9294053_impact_dataset" for source in catalog["sources"])


def test_specialized_queries_prefer_new_primary_experiment_sources():
    assert _preferred_source_ids("天然橡胶炭黑交联密度") == [
        "tire_pmc_10490132_thermal_aging"
    ]
    assert "brake_nasa_tn_d_8006" in _preferred_source_ids("碳石墨剪切膜破坏")
    assert "composite_pmc_6865209_bvid_reconstruction" in _preferred_source_ids(
        "BVID 多层分层重构"
    )


def test_literature_experiment_cards_are_traceable_and_bounded():
    payload = list_literature_experiments()

    assert payload["count"] == 5
    assert payload["reviewed_count"] == 5
    assert payload["review_status"] == "expert_reviewed"
    assert {record["domain"] for record in payload["records"]} == {
        "tire",
        "brake",
        "composite",
    }
    assert all(record["evidence_ids"] for record in payload["records"])
    assert all(record["source_locators"] for record in payload["records"])
    assert all(record["limitations"] for record in payload["records"])
    assert all(record["review_status"] == "expert_reviewed" for record in payload["records"])
    assert all(record["reviewed_at"] for record in payload["records"])
    assert all(record["review_scope"] for record in payload["records"])


def test_preferred_sources_include_faa_maintenance_excerpts():
    assert _preferred_source_ids("复材敲击法与 coin tap 检查") == [
        "composite_faa_h_8083_31b_ch7_ndi"
    ]
    assert _preferred_source_ids("刹车衬片磨损和刹车放气") == [
        "brake_faa_h_8083_31b_ch13_service"
    ]


def test_query_expansion_covers_maintenance_training_terms():
    expanded = _expand_query_terms(
        ["刹车衬片", "刹车放气", "敲击检测"],
        "识别复材分层和刹车过热后的检查边界",
        "机务维修新员工",
    )
    assert "wear indicator" in expanded
    assert "pressure bleeding" in expanded
    assert "coin tap" in expanded
    assert "rejected takeoff inspection" in expanded


def test_literature_evidence_evaluation_cases_cover_reviewed_sources():
    project_root = Path(__file__).resolve().parents[2]
    cases = json.loads(
        (project_root / "evaluation" / "literature_evidence_eval_cases.json").read_text(
            encoding="utf-8"
        )
    )["cases"]
    records = list_literature_experiments()["records"]
    reviewed_sources = {record["source_id"] for record in records}

    assert len(cases) == 10
    assert {case["expected_source_id"] for case in cases} == reviewed_sources
    assert all(
        case["expected_source_id"]
        in _preferred_source_ids(" ".join(case["weak_points"] + [case["learning_goal"]]))
        for case in cases
    )
