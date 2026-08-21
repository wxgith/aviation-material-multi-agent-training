from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.search.retriever import retrieve_with_rag_metadata


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EVALUATION_DIR = PROJECT_ROOT / "evaluation"
CASES_PATH = EVALUATION_DIR / "literature_evidence_eval_cases.json"
RECORDS_PATH = PROJECT_ROOT / "knowledge_corpus" / "literature_evidence" / "experiment_records.json"
MANIFEST_PATH = PROJECT_ROOT / "knowledge_corpus" / "index_manifest.json"
RESULTS_PATH = EVALUATION_DIR / "literature_evidence_results.json"
SUMMARY_PATH = EVALUATION_DIR / "literature_evidence_summary.md"


def run_evaluation() -> dict[str, Any]:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]
    records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    records_by_id = {record["record_id"]: record for record in records}
    manifest_ids = _manifest_ids(manifest)

    results = []
    for case in cases:
        retrieval = retrieve_with_rag_metadata(
            domain=case["domain"],
            weak_points=case["weak_points"],
            learning_goal=case["learning_goal"],
            learner_type=case["learner_type"],
            top_k=5,
        )
        source_ids = [chunk.get("source_id", "") for chunk in retrieval["chunks"]]
        evidence_ids = retrieval["evidence_ids"]
        record = records_by_id[case["expected_record_id"]]
        result = {
            "id": case["id"],
            "domain": case["domain"],
            "expected_source_id": case["expected_source_id"],
            "actual_source_ids": source_ids,
            "actual_evidence_ids": evidence_ids,
            "source_hit": case["expected_source_id"] in source_ids,
            "evidence_traceable": bool(evidence_ids) and all(item in manifest_ids for item in evidence_ids),
            "record_reviewed": record.get("review_status") == "expert_reviewed",
            "record_bounded": bool(record.get("limitations")) and bool(record.get("review_scope")),
            "knowledge_source": retrieval["knowledge_source"],
            "effective_retrieval_mode": retrieval["effective_retrieval_mode"],
        }
        result["passed"] = all(
            result[key]
            for key in ("source_hit", "evidence_traceable", "record_reviewed", "record_bounded")
        )
        results.append(result)

    total = len(results)
    metrics = {
        "case_count": total,
        "source_hit_rate": _rate(results, "source_hit"),
        "evidence_traceability_rate": _rate(results, "evidence_traceable"),
        "expert_review_coverage": _rate(results, "record_reviewed"),
        "boundary_statement_coverage": _rate(results, "record_bounded"),
        "elasticsearch_usage_rate": round(
            sum(item["knowledge_source"] == "elasticsearch" for item in results) / total, 4
        ) if total else 0.0,
    }
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation_scope": "expert_reviewed_published_literature_experiment_evidence",
        "metrics": metrics,
        "automated_status": "passed" if all(item["passed"] for item in results) else "needs_review",
        "cases": results,
    }
    RESULTS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    SUMMARY_PATH.write_text(_render_summary(payload), encoding="utf-8")
    return payload


def _manifest_ids(manifest: Any) -> set[str]:
    if isinstance(manifest, list):
        return {item.get("id", item.get("evidence_id", "")) for item in manifest}
    chunks = manifest.get("chunks", manifest.get("items", []))
    return {item.get("id", item.get("evidence_id", "")) for item in chunks}


def _rate(results: list[dict[str, Any]], key: str) -> float:
    return round(sum(bool(item[key]) for item in results) / len(results), 4) if results else 0.0


def _render_summary(payload: dict[str, Any]) -> str:
    metrics = payload["metrics"]
    rows = [
        "# 公开文献实验证据专项测评",
        "",
        f"运行时间：`{payload['generated_at']}`",
        "",
        "| 指标 | 结果 |",
        "| --- | ---: |",
        f"| 测评用例 | {metrics['case_count']} |",
        f"| 文献来源 Top-5 命中率 | {metrics['source_hit_rate']:.0%} |",
        f"| evidence_id 可追溯率 | {metrics['evidence_traceability_rate']:.0%} |",
        f"| 实验卡人工复核覆盖率 | {metrics['expert_review_coverage']:.0%} |",
        f"| 适用边界说明覆盖率 | {metrics['boundary_statement_coverage']:.0%} |",
        f"| Elasticsearch 使用率 | {metrics['elasticsearch_usage_rate']:.0%} |",
        "",
        f"自动化结论：`{payload['automated_status']}`。",
        "",
        "人工复核确认的是文献参数转录、来源定位与适用边界，不代表项目团队重复开展了原论文试验。",
        "",
        "## 用例明细",
        "",
        "| 用例 | 领域 | 期望来源 | 命中 | 知识来源 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in payload["cases"]:
        rows.append(
            f"| {item['id']} | {item['domain']} | {item['expected_source_id']} | "
            f"{'通过' if item['source_hit'] else '未命中'} | {item['knowledge_source']} |"
        )
    return "\n".join(rows) + "\n"


def main() -> None:
    payload = run_evaluation()
    print(json.dumps(payload["metrics"], ensure_ascii=False, indent=2))
    print(f"automated_status={payload['automated_status']}")


if __name__ == "__main__":
    main()
