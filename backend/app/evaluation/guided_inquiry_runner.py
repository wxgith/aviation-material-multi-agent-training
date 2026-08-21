from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.session_store import session_store


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EVALUATION_DIR = PROJECT_ROOT / "evaluation"
CASES_PATH = EVALUATION_DIR / "guided_inquiry_eval_cases.json"
RESULTS_PATH = EVALUATION_DIR / "guided_inquiry_results.json"
SUMMARY_PATH = EVALUATION_DIR / "guided_inquiry_summary.md"
EXPECTED_AGENTS = [
    "材料领域路由 Agent",
    "专业知识检索 Agent",
    "启发式讲解 Agent",
    "追问审核纠偏 Agent",
    "追问路径决策 Agent",
]


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
    session_store.clear()
    client = TestClient(app)
    try:
        results = [_run_case(client, case) for case in cases]
    finally:
        for key, value in original.items():
            setattr(settings, key, value)
        session_store.clear()

    metrics = _metrics(results)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "elasticsearch" if use_es else "json-fallback",
        "automated_status": "passed" if all(item["passed"] for item in results) else "needs_review",
        "metrics": metrics,
        "cases": results,
    }
    RESULTS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    SUMMARY_PATH.write_text(_render_summary(payload), encoding="utf-8")
    return payload


def _run_case(client: TestClient, case: dict[str, Any]) -> dict[str, Any]:
    profiles = client.get("/api/profiles").json()
    profile = next(item for item in profiles if item["profile_id"] == case["profile_id"])
    questions = client.get("/api/questions", params={"domain": case["domain"]}).json()
    answers = [
        {
            "question_id": question["id"],
            "answer": question["answer"] if case["diagnosis_mode"] == "strong" else "__wrong__",
        }
        for question in questions
    ]
    diagnosis_response = client.post(
        "/api/diagnosis",
        json={
            "profile_id": profile["profile_id"],
            "profile_override": profile,
            "domain": case["domain"],
            "answers": answers,
        },
    )
    diagnosis = diagnosis_response.json()
    run_response = client.post(
        "/api/agent/run",
        json={
            "profile_id": profile["profile_id"],
            "profile_override": profile,
            "domain": case["domain"],
            "diagnosis_result": diagnosis,
            "learning_goal": profile["default_goal"],
        },
    )
    session_id = run_response.json()["session_id"]
    ask_response = client.post(
        f"/api/sessions/{session_id}/ask",
        json={"question": case["question"]},
    )
    payload = ask_response.json() if ask_response.status_code == 200 else {}
    agent_names = [item.get("agent_name") for item in payload.get("agent_steps", [])]
    snippet_ids = {item.get("evidence_id") for item in payload.get("evidence_snippets", [])}
    evidence_ids = payload.get("evidence_ids", [])
    review = payload.get("review", {})
    searchable = " ".join(
        [payload.get("answer", "")]
        + payload.get("evidence_titles", [])
        + [item.get("snippet", "") for item in payload.get("evidence_snippets", [])]
    )
    checks = {
        "api_success": ask_response.status_code == 200,
        "agent_complete": agent_names == EXPECTED_AGENTS,
        "evidence_present": bool(evidence_ids),
        "citation_closed": bool(evidence_ids) and all(item in snippet_ids for item in evidence_ids),
        "boundary_complete": len(payload.get("boundaries", [])) >= 2,
        "review_passed": bool(review.get("approved")),
        "audit_complete": bool(payload.get("generation_audit", {}).get("prompt_version")),
        "personalization_match": case["expected_personalization"] in payload.get("explanation_level", ""),
        "topic_coverage": any(topic.lower() in searchable.lower() for topic in case["expected_topics"]),
        "decision_match": payload.get("next_action") in case["expected_next_actions"],
        "security_flags_match": all(
            flag in review.get("input_risk_flags", [])
            for flag in case.get("security_expectations", [])
        ),
    }
    return {
        "id": case["id"],
        "profile_id": case["profile_id"],
        "domain": case["domain"],
        "question": case["question"],
        "diagnosis_score": diagnosis.get("score"),
        "knowledge_source": payload.get("knowledge_source"),
        "retrieval_mode": payload.get("retrieval_mode"),
        "evidence_ids": evidence_ids,
        "next_action": payload.get("next_action"),
        "checks": checks,
        "passed": all(checks.values()),
    }


def _metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)

    def rate(key: str) -> float:
        return round(sum(item["checks"][key] for item in results) / total, 4) if total else 0.0

    return {
        "case_count": total,
        "passed_cases": sum(item["passed"] for item in results),
        "pass_rate": round(sum(item["passed"] for item in results) / total, 4) if total else 0.0,
        "agent_completeness_rate": rate("agent_complete"),
        "evidence_closure_rate": rate("citation_closed"),
        "boundary_coverage_rate": rate("boundary_complete"),
        "review_pass_rate": rate("review_passed"),
        "personalization_match_rate": rate("personalization_match"),
        "decision_accuracy": rate("decision_match"),
        "security_control_rate": rate("security_flags_match"),
        "elasticsearch_usage_rate": round(
            sum(item["knowledge_source"] == "elasticsearch" for item in results) / total, 4
        ) if total else 0.0,
    }


def _render_summary(payload: dict[str, Any]) -> str:
    metrics = payload["metrics"]
    rows = [
        "# 动态追问与 RAG 约束专项测评",
        "",
        f"运行时间：`{payload['generated_at']}`  ",
        f"运行模式：`{payload['mode']}`  ",
        f"自动化结论：`{payload['automated_status']}`",
        "",
        "| 指标 | 结果 |",
        "| --- | ---: |",
        f"| 用例数 | {metrics['case_count']} |",
        f"| 通过数 | {metrics['passed_cases']} |",
        f"| 总通过率 | {metrics['pass_rate']:.0%} |",
        f"| 5 Agent 完整率 | {metrics['agent_completeness_rate']:.0%} |",
        f"| 证据引用闭合率 | {metrics['evidence_closure_rate']:.0%} |",
        f"| 适用边界覆盖率 | {metrics['boundary_coverage_rate']:.0%} |",
        f"| 审核通过率 | {metrics['review_pass_rate']:.0%} |",
        f"| 画像适配率 | {metrics['personalization_match_rate']:.0%} |",
        f"| 路径决策准确率 | {metrics['decision_accuracy']:.0%} |",
        f"| 越权提示防护率 | {metrics['security_control_rate']:.0%} |",
        f"| Elasticsearch 使用率 | {metrics['elasticsearch_usage_rate']:.0%} |",
        "",
        "> 本表为规则可自动验证项；专业事实准确性仍以已建立的专家复核表为准。",
        "",
        "## 用例执行明细",
        "",
        "| 用例 | 画像 | 领域 | 来源 | 证据闭合 | 审核 | 决策 | 结论 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in payload["cases"]:
        rows.append(
            f"| {item['id']} | {item['profile_id']} | {item['domain']} | "
            f"{item['knowledge_source']} | {'通过' if item['checks']['citation_closed'] else '失败'} | "
            f"{'通过' if item['checks']['review_passed'] else '失败'} | {item['next_action']} | "
            f"{'通过' if item['passed'] else '待复核'} |"
        )
    return "\n".join(rows) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="运行动态追问与 RAG 约束专项测评。")
    parser.add_argument("--use-es", action="store_true", help="启用 Elasticsearch 检索。")
    args = parser.parse_args()
    payload = run_evaluation(use_es=args.use_es)
    print(json.dumps(payload["metrics"], ensure_ascii=False, indent=2))
    print(f"automated_status={payload['automated_status']}")


if __name__ == "__main__":
    main()
