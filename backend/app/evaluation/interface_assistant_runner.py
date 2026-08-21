from __future__ import annotations

import json
from time import perf_counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EVALUATION_DIR = PROJECT_ROOT / "evaluation"
CASES_PATH = EVALUATION_DIR / "interface_assistant_eval_cases.json"
RESULTS_PATH = EVALUATION_DIR / "interface_assistant_eval_results.json"
SUMMARY_PATH = EVALUATION_DIR / "interface_assistant_eval_summary.md"


def run_evaluation(*, use_es: bool = False) -> dict[str, Any]:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]
    original = {
        "database_enabled": settings.database_enabled,
        "data_backend": settings.data_backend,
        "es_enabled": settings.es_enabled,
        "llm_enabled": settings.llm_enabled,
    }
    settings.database_enabled = False
    settings.data_backend = "json"
    settings.es_enabled = use_es
    settings.llm_enabled = False
    client = TestClient(app)
    try:
        results = [_run_case(client, case) for case in cases]
    finally:
        for key, value in original.items():
            setattr(settings, key, value)

    passed = sum(item["passed"] for item in results)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "elasticsearch + mock-llm" if use_es else "json-fallback + mock-llm",
        "status": "passed" if passed == len(results) else "needs_review",
        "metrics": {
            "case_count": len(results),
            "passed_cases": passed,
            "pass_rate": round(passed / len(results), 4) if results else 0.0,
            "routing_accuracy": _rate(results, "answer_type_match"),
            "agent_completeness": _rate(results, "agent_count_match"),
            "keyword_coverage": _rate(results, "keyword_coverage"),
            "evidence_availability": _rate(
                [item for item in results if item["requires_evidence"]], "evidence_requirement"
            ),
            "boundary_coverage": _rate(results, "boundary_present"),
            "evidence_title_alignment": _rate(results, "evidence_title_alignment"),
            "navigation_accuracy": _rate(results, "recommended_view_match"),
            "safety_control_rate": _rate(results, "risk_flags_match"),
            "forbidden_output_absence_rate": _rate(results, "forbidden_absent"),
            "average_latency_ms": round(sum(item["latency_ms"] for item in results) / len(results)) if results else 0,
            "p95_latency_ms": _percentile([item["latency_ms"] for item in results], 0.95),
            "by_category": _category_metrics(results),
        },
        "cases": results,
    }
    results_path = RESULTS_PATH if not use_es else EVALUATION_DIR / "interface_assistant_eval_results_es.json"
    summary_path = SUMMARY_PATH if not use_es else EVALUATION_DIR / "interface_assistant_eval_summary_es.md"
    results_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path.write_text(_render_summary(payload), encoding="utf-8")
    return payload


def _run_case(client: TestClient, case: dict[str, Any]) -> dict[str, Any]:
    started = perf_counter()
    response = client.post(
        "/api/assistant/ask",
        json={"question": case["question"], "context": case["context"]},
    )
    payload = response.json() if response.status_code == 200 else {}
    latency_ms = round((perf_counter() - started) * 1000)
    searchable = " ".join([payload.get("answer", ""), *payload.get("evidence_titles", [])])
    review_steps = [
        item for item in payload.get("agent_steps", [])
        if item.get("agent_name") == "追问审核纠偏 Agent"
    ]
    risk_flags = review_steps[-1].get("details", {}).get("input_risk_flags", []) if review_steps else []
    expected_view = case.get("expected_view")
    forbidden = case.get("forbidden_terms", [])
    expected_flags = case.get("expected_risk_flags", [])
    evidence_ids = payload.get("evidence_ids", [])
    evidence_titles = payload.get("evidence_titles", [])
    checks = {
        "api_success": response.status_code == 200,
        "answer_type_match": payload.get("answer_type") == case["expected_answer_type"],
        "agent_count_match": len(payload.get("agent_steps", [])) == case["expected_agent_count"],
        "keyword_coverage": all(word.lower() in searchable.lower() for word in case["expected_keywords"]),
        "evidence_requirement": bool(evidence_ids) if case["requires_evidence"] else True,
        "boundary_present": bool(payload.get("boundaries")),
        "evidence_title_alignment": len(evidence_ids) == len(evidence_titles),
        "recommended_view_match": expected_view is None or payload.get("recommended_view") == expected_view,
        "risk_flags_match": all(flag in risk_flags for flag in expected_flags),
        "forbidden_absent": all(term.lower() not in searchable.lower() for term in forbidden),
    }
    return {
        "id": case["id"],
        "category": case["category"],
        "question": case["question"],
        "answer_type": payload.get("answer_type"),
        "generation_mode": payload.get("generation_mode"),
        "knowledge_source": payload.get("knowledge_source"),
        "evidence_ids": payload.get("evidence_ids", []),
        "recommended_view": payload.get("recommended_view"),
        "risk_flags": risk_flags,
        "requires_evidence": case["requires_evidence"],
        "latency_ms": latency_ms,
        "checks": checks,
        "passed": all(checks.values()),
    }


def _rate(results: list[dict[str, Any]], key: str) -> float:
    return round(sum(item["checks"][key] for item in results) / len(results), 4) if results else 0.0


def _percentile(values: list[int], quantile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * quantile)))
    return ordered[index]


def _category_metrics(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    categories = sorted({item["category"] for item in results})
    return {
        category: {
            "total": len(items := [item for item in results if item["category"] == category]),
            "passed": sum(item["passed"] for item in items),
            "pass_rate": round(sum(item["passed"] for item in items) / len(items), 4),
        }
        for category in categories
    }


def _render_summary(payload: dict[str, Any]) -> str:
    metrics = payload["metrics"]
    rows = [
        "# 全局上下文问答助手专项测评",
        "",
        f"运行时间：`{payload['generated_at']}`  ",
        f"运行模式：`{payload['mode']}`  ",
        f"自动化结论：`{payload['status']}`",
        "",
        "| 指标 | 结果 |",
        "| --- | ---: |",
        f"| 用例数 | {metrics['case_count']} |",
        f"| 通过数 | {metrics['passed_cases']} |",
        f"| 总通过率 | {metrics['pass_rate']:.0%} |",
        f"| 意图路由准确率 | {metrics['routing_accuracy']:.0%} |",
        f"| Agent 步骤完整率 | {metrics['agent_completeness']:.0%} |",
        f"| 关键内容覆盖率 | {metrics['keyword_coverage']:.0%} |",
        f"| 领域问答证据可用率 | {metrics['evidence_availability']:.0%} |",
        f"| 回答边界覆盖率 | {metrics['boundary_coverage']:.0%} |",
        f"| 证据 ID/标题对齐率 | {metrics['evidence_title_alignment']:.0%} |",
        f"| 页面推荐准确率 | {metrics['navigation_accuracy']:.0%} |",
        f"| 越权风险标记率 | {metrics['safety_control_rate']:.0%} |",
        f"| 禁止结论未出现率 | {metrics['forbidden_output_absence_rate']:.0%} |",
        f"| 平均响应耗时 | {metrics['average_latency_ms']} ms |",
        f"| P95 响应耗时 | {metrics['p95_latency_ms']} ms |",
        "",
        "## 用例明细",
        "",
        "| 用例 | 类型 | 回答路由 | 来源 | 证据数 | 耗时 | 结论 |",
        "| --- | --- | --- | --- | ---: | ---: | --- |",
    ]
    for item in payload["cases"]:
        rows.append(
            f"| {item['id']} | {item['category']} | {item['answer_type']} | "
            f"{item['knowledge_source']} | {len(item['evidence_ids'])} | {item['latency_ms']} ms | "
            f"{'通过' if item['passed'] else '待复核'} |"
        )
    rows.extend([
        "",
        "> 领域专业事实仍需结合既有专家复核表确认；本测评验证意图路由、上下文使用、证据返回和结构完整性。",
    ])
    return "\n".join(rows) + "\n"


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="运行全局上下文助手专项测评。")
    parser.add_argument("--use-es", action="store_true", help="使用 Elasticsearch 工程检索。")
    args = parser.parse_args()
    payload = run_evaluation(use_es=args.use_es)
    print(json.dumps(payload["metrics"], ensure_ascii=False, indent=2))
    print(f"status={payload['status']}")


if __name__ == "__main__":
    main()
