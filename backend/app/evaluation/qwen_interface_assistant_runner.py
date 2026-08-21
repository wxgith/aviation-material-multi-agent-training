from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EVALUATION_DIR = PROJECT_ROOT / "evaluation"
CASES_PATH = EVALUATION_DIR / "qwen_interface_assistant_eval_cases.json"
RESULTS_PATH = EVALUATION_DIR / "qwen_interface_assistant_results.json"
SUMMARY_PATH = EVALUATION_DIR / "qwen_interface_assistant_summary.md"


def run_evaluation() -> dict[str, Any]:
    if not settings.llm_enabled or not settings.llm_model:
        raise RuntimeError("真实模型未启用，请配置 LLM_ENABLED=true 和 LLM_MODEL。")
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]
    original = {
        "database_enabled": settings.database_enabled,
        "data_backend": settings.data_backend,
        "es_enabled": settings.es_enabled,
    }
    settings.database_enabled = False
    settings.data_backend = "json"
    settings.es_enabled = True
    client = TestClient(app)
    try:
        results = [_run_case(client, case) for case in cases]
    finally:
        for key, value in original.items():
            setattr(settings, key, value)

    passed = sum(item["passed"] for item in results)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": settings.llm_model,
        "status": "passed" if passed == len(results) else "needs_review",
        "professional_review_status": "待领域专家抽样确认最终修订稿",
        "metrics": {
            "case_count": len(results),
            "passed_cases": passed,
            "pass_rate": round(passed / len(results), 4),
            "real_llm_usage_rate": _rate(results, "real_llm_used"),
            "elasticsearch_usage_rate": _rate(results, "elasticsearch_used"),
            "agent_completeness_rate": _rate(results, "agent_complete"),
            "evidence_closure_rate": _rate(results, "evidence_closed"),
            "boundary_coverage_rate": _rate(results, "boundary_present"),
            "input_understanding_rate": _rate(results, "expected_terms_present"),
            "risk_control_rate": _rate(results, "risk_flags_match"),
            "forbidden_output_absence_rate": _rate(results, "forbidden_absent"),
            "average_generation_latency_ms": round(sum(item["generation_latency_ms"] for item in results) / len(results)),
            "average_review_latency_ms": round(sum(item["review_latency_ms"] for item in results) / len(results)),
            "review_rejection_count": sum(item["candidate_rejected"] for item in results),
        },
        "cases": results,
    }
    RESULTS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    SUMMARY_PATH.write_text(_render_summary(payload), encoding="utf-8")
    return payload


def _run_case(client: TestClient, case: dict[str, Any]) -> dict[str, Any]:
    response = client.post("/api/assistant/ask", json={"question": case["question"], "context": case["context"]})
    payload = response.json() if response.status_code == 200 else {}
    steps = payload.get("agent_steps", [])
    review_step = next((step for step in steps if step.get("agent_name") == "追问审核纠偏 Agent"), {})
    tutor_step = next((step for step in steps if step.get("agent_name") == "启发式讲解 Agent"), {})
    review = review_step.get("details", {})
    generation_audit = tutor_step.get("details", {}).get("generation_audit", {})
    review_audit = review.get("review_audit", {})
    answer_text = str(payload.get("answer", ""))
    # Template fallback echoes the learner question in its first sentence. Do
    # not count that echo as proof that the answer understood the requested terms.
    if answer_text.startswith("针对“") and "”，" in answer_text:
        answer_text = answer_text.split("”，", 1)[1]
    searchable = " ".join([answer_text, *payload.get("boundaries", []), *payload.get("evidence_titles", [])]).lower()
    expected_all = case.get("expected_terms_all", [])
    expected_any = case.get("expected_terms_any", [])
    evidence_ids = payload.get("evidence_ids", [])
    checks = {
        "api_success": response.status_code == 200,
        "answer_type_match": payload.get("answer_type") == "domain-grounded",
        "real_llm_used": payload.get("generation_mode") in {"llm", "review-template-fallback"},
        "elasticsearch_used": payload.get("knowledge_source") == "elasticsearch",
        "agent_complete": len(steps) == 5,
        "evidence_closed": bool(evidence_ids) and len(evidence_ids) == len(payload.get("evidence_titles", [])),
        "boundary_present": len(payload.get("boundaries", [])) >= 2,
        "expected_terms_present": all(term.lower() in searchable for term in expected_all) and (not expected_any or any(term.lower() in searchable for term in expected_any)),
        "risk_flags_match": all(flag in review.get("input_risk_flags", []) for flag in case.get("expected_risk_flags", [])),
        "forbidden_absent": all(term.lower() not in searchable for term in case.get("forbidden_terms", [])),
        "audit_success": (
            generation_audit.get("outcome") == "success"
            or generation_audit.get("candidate_generation_audit", {}).get("outcome") == "success"
        ),
        "review_completed": review.get("status") in {"通过", "通过，附限制说明", "通过，已降级重生", "需纠偏"},
    }
    return {
        "id": case["id"],
        "question": case["question"],
        "domain": case["context"]["domain"],
        "answer": payload.get("answer", ""),
        "evidence_ids": evidence_ids,
        "boundaries": payload.get("boundaries", []),
        "generation_mode": payload.get("generation_mode"),
        "knowledge_source": payload.get("knowledge_source"),
        "review_status": review.get("status"),
        "candidate_rejected": bool(review.get("candidate_rejected")),
        "revision_applied": bool(review.get("revision_applied")),
        "risk_points": review.get("risk_points", []),
        "risk_flags": review.get("input_risk_flags", []),
        "generation_latency_ms": int(generation_audit.get("latency_ms") or 0),
        "review_latency_ms": int(review_audit.get("latency_ms") or 0),
        "checks": checks,
        "passed": all(checks.values()),
        "expert_verdict": "待人工复核",
    }


def _rate(results: list[dict[str, Any]], key: str) -> float:
    return round(sum(item["checks"][key] for item in results) / len(results), 4) if results else 0.0


def _render_summary(payload: dict[str, Any]) -> str:
    m = payload["metrics"]
    rows = [
        "# Qwen 全局上下文助手真实回答抽样",
        "",
        f"运行时间：`{payload['generated_at']}`  ",
        f"模型：`{payload['model']}`  ",
        f"机器检查：`{payload['status']}`  ",
        f"专业复核：`{payload['professional_review_status']}`",
        "",
        "| 指标 | 结果 |",
        "| --- | ---: |",
        f"| 用例数 | {m['case_count']} |",
        f"| 通过数 | {m['passed_cases']} |",
        f"| 机器通过率 | {m['pass_rate']:.0%} |",
        f"| 真实 LLM 使用率 | {m['real_llm_usage_rate']:.0%} |",
        f"| Elasticsearch 使用率 | {m['elasticsearch_usage_rate']:.0%} |",
        f"| 5 Agent 完整率 | {m['agent_completeness_rate']:.0%} |",
        f"| 证据闭合率 | {m['evidence_closure_rate']:.0%} |",
        f"| 边界覆盖率 | {m['boundary_coverage_rate']:.0%} |",
        f"| 输入理解率 | {m['input_understanding_rate']:.0%} |",
        f"| 风险控制率 | {m['risk_control_rate']:.0%} |",
        f"| 禁止结论未出现率 | {m['forbidden_output_absence_rate']:.0%} |",
        f"| 平均生成耗时 | {m['average_generation_latency_ms']} ms |",
        f"| 平均审核耗时 | {m['average_review_latency_ms']} ms |",
        f"| 审核驳回并模板重生 | {m['review_rejection_count']} 条 |",
        "",
        "| 用例 | 领域 | 模式 | 证据数 | 审核 | 结论 |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for item in payload["cases"]:
        rows.append(
            f"| {item['id']} | {item['domain']} | {item['generation_mode']} | {len(item['evidence_ids'])} | "
            f"{item['review_status']} | {'通过' if item['passed'] else '待检查'} |"
        )
    rows.extend(["", "> 机器检查不替代领域专家对专业事实与修订合理性的最终确认。"])
    return "\n".join(rows) + "\n"


def main() -> None:
    payload = run_evaluation()
    print(json.dumps(payload["metrics"], ensure_ascii=False, indent=2))
    print(f"status={payload['status']}")


if __name__ == "__main__":
    main()
