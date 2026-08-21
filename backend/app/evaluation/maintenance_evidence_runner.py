from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.search.retriever import retrieve_with_rag_metadata


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EVALUATION_DIR = PROJECT_ROOT / "evaluation"
CASES_PATH = EVALUATION_DIR / "maintenance_evidence_eval_cases.json"
REGISTRY_PATH = PROJECT_ROOT / "knowledge_corpus" / "source_registry.json"
MANIFEST_PATH = PROJECT_ROOT / "knowledge_corpus" / "index_manifest.json"
RESULTS_PATH = EVALUATION_DIR / "maintenance_evidence_results.json"
SUMMARY_PATH = EVALUATION_DIR / "maintenance_evidence_summary.md"


def run_evaluation() -> dict[str, Any]:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))["sources"]
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    sources = {source["source_id"]: source for source in registry}
    manifest_ids = {chunk["id"] for chunk in manifest["chunks"]}

    results = []
    for case in cases:
        retrieval = retrieve_with_rag_metadata(
            domain=case["domain"],
            weak_points=case["weak_points"],
            learning_goal=case["learning_goal"],
            learner_type=case["learner_type"],
            top_k=5,
        )
        actual_source_ids = [chunk.get("source_id", "") for chunk in retrieval["chunks"]]
        source = sources[case["expected_source_id"]]
        evidence_ids = retrieval["evidence_ids"]
        item = {
            "id": case["id"],
            "domain": case["domain"],
            "expected_source_id": case["expected_source_id"],
            "actual_source_ids": actual_source_ids,
            "actual_evidence_ids": evidence_ids,
            "source_hit": case["expected_source_id"] in actual_source_ids,
            "evidence_traceable": bool(evidence_ids)
            and all(evidence_id in manifest_ids for evidence_id in evidence_ids),
            "official_source": source.get("source_authority") == "official_primary",
            "boundary_documented": _has_boundary_statement(source.get("notes", "")),
            "knowledge_source": retrieval["knowledge_source"],
            "effective_retrieval_mode": retrieval["effective_retrieval_mode"],
        }
        item["passed"] = all(
            item[key]
            for key in (
                "source_hit",
                "evidence_traceable",
                "official_source",
                "boundary_documented",
            )
        )
        results.append(item)

    metrics = {
        "case_count": len(results),
        "source_hit_rate": _rate(results, "source_hit"),
        "evidence_traceability_rate": _rate(results, "evidence_traceable"),
        "official_source_rate": _rate(results, "official_source"),
        "boundary_statement_coverage": _rate(results, "boundary_documented"),
        "elasticsearch_usage_rate": round(
            sum(item["knowledge_source"] == "elasticsearch" for item in results)
            / len(results),
            4,
        )
        if results
        else 0.0,
    }
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation_scope": "official_maintenance_training_evidence",
        "metrics": metrics,
        "automated_status": "passed" if all(item["passed"] for item in results) else "needs_review",
        "cases": results,
    }
    RESULTS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    SUMMARY_PATH.write_text(_render_summary(payload), encoding="utf-8")
    return payload


def _rate(results: list[dict[str, Any]], key: str) -> float:
    return round(sum(bool(item[key]) for item in results) / len(results), 4) if results else 0.0


def _has_boundary_statement(notes: str) -> bool:
    lowered = notes.lower()
    return bool(notes) and any(marker in lowered for marker in ("must", "not as", "cannot replace"))


def _render_summary(payload: dict[str, Any]) -> str:
    metrics = payload["metrics"]
    rows = [
        "# FAA 维修训练证据专项测评",
        "",
        f"运行时间：`{payload['generated_at']}`",
        "",
        "| 指标 | 结果 |",
        "| --- | ---: |",
        f"| 测评用例 | {metrics['case_count']} |",
        f"| 官方来源 Top-5 命中率 | {metrics['source_hit_rate']:.0%} |",
        f"| evidence_id 可追溯率 | {metrics['evidence_traceability_rate']:.0%} |",
        f"| 官方来源标识率 | {metrics['official_source_rate']:.0%} |",
        f"| 使用边界说明覆盖率 | {metrics['boundary_statement_coverage']:.0%} |",
        f"| Elasticsearch 使用率 | {metrics['elasticsearch_usage_rate']:.0%} |",
        "",
        f"自动化结论：`{payload['automated_status']}`。",
        "",
        "这些资料用于训练检查思路，不能替代具体机型的现行制造商手册、维修方案或批准数据。",
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
