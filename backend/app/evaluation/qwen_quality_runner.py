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
CASES_PATH = EVALUATION_DIR / "qwen_quality_eval_cases.json"
RESULTS_PATH = EVALUATION_DIR / "qwen_quality_results.json"
SUMMARY_PATH = EVALUATION_DIR / "qwen_quality_summary.md"
RUNS_DIR = EVALUATION_DIR / "qwen_quality_runs"
EXPECTED_INQUIRY_AGENTS = [
    "材料领域路由 Agent",
    "专业知识检索 Agent",
    "启发式讲解 Agent",
    "追问审核纠偏 Agent",
    "追问路径决策 Agent",
]


def run_evaluation(*, base_url: str | None = None) -> dict[str, Any]:
    dataset = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    original = {
        "database_enabled": settings.database_enabled,
        "data_backend": settings.data_backend,
        "es_enabled": settings.es_enabled,
        "llm_enabled": settings.llm_enabled,
    }
    if not settings.llm_enabled or not settings.llm_model:
        raise RuntimeError("真实模型未启用，请先配置 LLM_ENABLED=true 和 LLM_MODEL。")

    settings.database_enabled = False
    settings.data_backend = "json"
    settings.es_enabled = True
    session_store.clear()
    client = TestClient(app, base_url=base_url or "http://testserver")
    results: list[dict[str, Any]] = []
    resource_check: dict[str, Any] = {}
    try:
        for scenario in dataset["scenarios"]:
            scenario_results, scenario_resource = _run_scenario(client, scenario)
            results.extend(scenario_results)
            if scenario_resource:
                resource_check = scenario_resource
    finally:
        for key, value in original.items():
            setattr(settings, key, value)
        session_store.clear()

    metrics = _metrics(results, resource_check)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": settings.llm_model,
        "knowledge_source_expected": "elasticsearch",
        "automated_status": (
            "passed" if all(item["machine_passed"] for item in results) else "needs_review"
        ),
        "professional_review_status": _professional_review_status(results),
        "resource_generation_check": resource_check,
        "metrics": metrics,
        "cases": results,
    }
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    run_name = datetime.now(timezone.utc).strftime("qwen_quality_%Y%m%dT%H%M%SZ.json")
    run_path = RUNS_DIR / run_name
    payload["run_artifact"] = str(run_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    run_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    RESULTS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    SUMMARY_PATH.write_text(_render_summary(payload), encoding="utf-8")
    return payload


def _run_scenario(
    client: TestClient, scenario: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    profiles = client.get("/api/profiles").json()
    profile = next(item for item in profiles if item["profile_id"] == scenario["profile_id"])
    questions = client.get("/api/questions", params={"domain": scenario["domain"]}).json()
    answers = [
        {
            "question_id": question["id"],
            "answer": (
                question["answer"]
                if scenario["diagnosis_mode"] == "strong"
                else "__wrong__"
            ),
        }
        for question in questions
    ]
    diagnosis_response = client.post(
        "/api/diagnosis",
        json={
            "profile_id": profile["profile_id"],
            "profile_override": profile,
            "domain": scenario["domain"],
            "answers": answers,
        },
    )
    diagnosis_response.raise_for_status()
    diagnosis = diagnosis_response.json()

    previous_llm_enabled = settings.llm_enabled
    settings.llm_enabled = bool(scenario.get("run_full_resource_generation"))
    try:
        run_response = client.post(
            "/api/agent/run",
            json={
                "profile_id": profile["profile_id"],
                "profile_override": profile,
                "domain": scenario["domain"],
                "diagnosis_result": diagnosis,
                "learning_goal": scenario["learning_goal"],
            },
        )
    finally:
        settings.llm_enabled = previous_llm_enabled
    run_response.raise_for_status()
    run_payload = run_response.json()
    session_id = run_payload["session_id"]
    resource_check: dict[str, Any] = {}
    if scenario.get("run_full_resource_generation"):
        resources = client.get(f"/api/sessions/{session_id}/resources").json()
        resource_check = {
            "session_id": session_id,
            "agent_step_count": len(run_payload.get("agent_steps", [])),
            "generation_mode": resources.get("generation_mode"),
            "audit_outcome": resources.get("generation_audit", {}).get("outcome"),
            "model": resources.get("generation_audit", {}).get("model"),
            "passed": (
                len(run_payload.get("agent_steps", [])) == 6
                and resources.get("generation_mode") == "llm"
                and resources.get("generation_audit", {}).get("outcome") == "success"
            ),
        }

    results = []
    for case in scenario["questions"]:
        response = client.post(
            f"/api/sessions/{session_id}/ask",
            json={"question": case["question"]},
        )
        payload = response.json() if response.status_code == 200 else {}
        results.append(_evaluate_case(case, scenario, diagnosis, response.status_code, payload))
    return results, resource_check


def _evaluate_case(
    case: dict[str, Any],
    scenario: dict[str, Any],
    diagnosis: dict[str, Any],
    status_code: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    answer = str(payload.get("answer", ""))
    boundaries = " ".join(str(item) for item in payload.get("boundaries", []))
    answer_for_checks = answer
    if answer_for_checks.startswith("针对“") and "”，" in answer_for_checks:
        answer_for_checks = answer_for_checks.split("”，", 1)[1]
    searchable = f"{answer_for_checks} {boundaries}".lower()
    evidence_ids = payload.get("evidence_ids", [])
    snippet_ids = {
        item.get("evidence_id") for item in payload.get("evidence_snippets", [])
    }
    review = payload.get("review", {})
    agent_names = [step.get("agent_name") for step in payload.get("agent_steps", [])]

    expected_all = case.get("expected_terms_all", [])
    expected_any = case.get("expected_terms_any", [])
    boundary_any = case.get("expected_boundary_any", [])
    forbidden = case.get("forbidden_terms", [])
    checks = {
        "api_success": status_code == 200,
        "real_llm_used": payload.get("generation_mode") in {"llm", "review-template-fallback"},
        "llm_audit_success": (
            payload.get("generation_audit", {}).get("outcome") == "success"
            or payload.get("generation_audit", {}).get("candidate_generation_audit", {}).get("outcome") == "success"
        ),
        "input_terms_all": all(term.lower() in searchable for term in expected_all),
        "input_terms_any": not expected_any or any(
            term.lower() in searchable for term in expected_any
        ),
        "boundary_response": not boundary_any or any(
            term.lower() in searchable for term in boundary_any
        ),
        "forbidden_absent": all(term.lower() not in searchable for term in forbidden),
        "evidence_present": bool(evidence_ids),
        "evidence_closed": bool(evidence_ids)
        and all(evidence_id in snippet_ids for evidence_id in evidence_ids),
        "elasticsearch_used": payload.get("knowledge_source") == "elasticsearch",
        "review_completed": bool(review.get("status")),
        "review_controlled": review.get("status") in {"通过", "通过，附限制说明", "通过，已降级重生", "需纠偏"},
        "risk_flags_match": all(
            flag in review.get("input_risk_flags", [])
            for flag in case.get("expected_risk_flags", [])
        ),
        "personalization_match": case.get("expected_personalization", "")
        in payload.get("explanation_level", ""),
        "agent_complete": agent_names == EXPECTED_INQUIRY_AGENTS,
        "answer_substantive": len(answer) >= 80,
    }
    dimensions = {
        "input_understanding": _rate(
            checks, ["input_terms_all", "input_terms_any", "answer_substantive"]
        ),
        "evidence_grounding": _rate(
            checks, ["evidence_present", "evidence_closed", "elasticsearch_used"]
        ),
        "professional_safety": _rate(
            checks, ["boundary_response", "forbidden_absent", "risk_flags_match"]
        ),
        "personalization": _rate(checks, ["personalization_match"]),
        "agent_execution": _rate(
            checks,
            [
                "api_success",
                "real_llm_used",
                "llm_audit_success",
                "review_completed",
                "review_controlled",
                "agent_complete",
            ],
        ),
    }
    machine_passed = all(checks.values())
    return {
        "id": case["id"],
        "scenario_id": scenario["id"],
        "profile_id": scenario["profile_id"],
        "domain": scenario["domain"],
        "diagnosis_score": diagnosis.get("score"),
        "question": case["question"],
        "answer": answer,
        "explanation_level": payload.get("explanation_level"),
        "evidence_ids": evidence_ids,
        "evidence_titles": payload.get("evidence_titles", []),
        "evidence_snippets": payload.get("evidence_snippets", []),
        "boundaries": payload.get("boundaries", []),
        "follow_up_question": payload.get("follow_up_question"),
        "practice_task": payload.get("practice_task"),
        "next_action": payload.get("next_action"),
        "generation_mode": payload.get("generation_mode"),
        "generation_audit": payload.get("generation_audit", {}),
        "retrieval_mode": payload.get("retrieval_mode"),
        "knowledge_source": payload.get("knowledge_source"),
        "review": review,
        "agent_names": agent_names,
        "checks": checks,
        "dimension_scores": dimensions,
        "machine_passed": machine_passed,
        "expert_verdict": "待人工复核",
        "expert_notes": "",
    }


def _rate(checks: dict[str, bool], keys: list[str]) -> float:
    return round(sum(bool(checks[key]) for key in keys) / len(keys), 4) if keys else 0.0


def _generation_latency(audit: dict[str, Any]) -> int:
    latency = int(audit.get("latency_ms", 0) or 0)
    if latency:
        return latency
    candidate = audit.get("candidate_generation_audit", {})
    return int(candidate.get("latency_ms", 0) or 0)


def _metrics(
    results: list[dict[str, Any]], resource_check: dict[str, Any]
) -> dict[str, Any]:
    total = len(results)

    def case_rate(key: str) -> float:
        return round(sum(item["checks"][key] for item in results) / total, 4) if total else 0.0

    def dimension_average(key: str) -> float:
        return round(
            sum(item["dimension_scores"][key] for item in results) / total, 4
        ) if total else 0.0

    return {
        "case_count": total,
        "machine_passed_cases": sum(item["machine_passed"] for item in results),
        "machine_pass_rate": round(
            sum(item["machine_passed"] for item in results) / total, 4
        ) if total else 0.0,
        "real_llm_usage_rate": case_rate("real_llm_used"),
        "elasticsearch_usage_rate": case_rate("elasticsearch_used"),
        "evidence_closure_rate": case_rate("evidence_closed"),
        "review_completion_rate": case_rate("review_completed"),
        "direct_review_pass_rate": round(
            sum(item["review"].get("candidate_rejected") is not True for item in results) / total,
            4,
        ) if total else 0.0,
        "risk_control_rate": case_rate("risk_flags_match"),
        "input_understanding_score": dimension_average("input_understanding"),
        "evidence_grounding_score": dimension_average("evidence_grounding"),
        "professional_safety_score": dimension_average("professional_safety"),
        "personalization_score": dimension_average("personalization"),
        "agent_execution_score": dimension_average("agent_execution"),
        "average_answer_latency_ms": round(
            sum(_generation_latency(item["generation_audit"]) for item in results) / total
        ) if total else 0,
        "average_review_latency_ms": round(
            sum(item["review"].get("review_audit", {}).get("latency_ms", 0) for item in results)
            / total
        ) if total else 0,
        "full_resource_generation_passed": bool(resource_check.get("passed")),
    }


def _professional_review_status(results: list[dict[str, Any]]) -> str:
    correction_count = sum(
        item.get("review", {}).get("candidate_rejected") is True for item in results
    )
    return f"{correction_count} 条经审核 Agent 驳回并由证据模板重生，仍待领域专家确认"


def _render_summary(payload: dict[str, Any]) -> str:
    metrics = payload["metrics"]
    rows = [
        "# Qwen 真实模型回答质量测评",
        "",
        f"运行时间：`{payload['generated_at']}`  ",
        f"模型：`{payload['model']}`  ",
        f"自动检查：`{payload['automated_status']}`  ",
        f"专业复核：`{payload['professional_review_status']}`",
        "",
        "> 自动检查验证结构、关键词、证据闭合、边界与安全规则；专业事实准确性仍需领域专家阅读原始回答后确认。",
        "",
        "## 汇总指标",
        "",
        "| 指标 | 结果 |",
        "| --- | ---: |",
        f"| 测试问题数 | {metrics['case_count']} |",
        f"| 机器检查通过数 | {metrics['machine_passed_cases']} |",
        f"| 机器检查通过率 | {metrics['machine_pass_rate']:.0%} |",
        f"| 真实 LLM 使用率 | {metrics['real_llm_usage_rate']:.0%} |",
        f"| Elasticsearch 使用率 | {metrics['elasticsearch_usage_rate']:.0%} |",
        f"| 证据引用闭合率 | {metrics['evidence_closure_rate']:.0%} |",
        f"| 候选回答直接通过率 | {metrics['direct_review_pass_rate']:.0%} |",
        f"| 输入理解得分 | {metrics['input_understanding_score']:.0%} |",
        f"| 证据约束得分 | {metrics['evidence_grounding_score']:.0%} |",
        f"| 专业安全得分 | {metrics['professional_safety_score']:.0%} |",
        f"| 画像适配得分 | {metrics['personalization_score']:.0%} |",
        f"| Agent 执行得分 | {metrics['agent_execution_score']:.0%} |",
        f"| 平均回答延迟 | {metrics['average_answer_latency_ms']} ms |",
        f"| 平均审核延迟 | {metrics['average_review_latency_ms']} ms |",
        f"| 6 Agent 真实资源生成 | {'通过' if metrics['full_resource_generation_passed'] else '未通过'} |",
        "",
        "## 逐题结果",
        "",
        "| 用例 | 领域 | 画像 | LLM | ES | 证据闭合 | 审核 | 机器结论 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in payload["cases"]:
        rows.append(
            f"| {item['id']} | {item['domain']} | {item['profile_id']} | "
            f"{item['generation_mode']} | {item['knowledge_source']} | "
            f"{'通过' if item['checks']['evidence_closed'] else '失败'} | "
            f"{item['review'].get('status', '缺失')} | "
            f"{'通过' if item['machine_passed'] else '待检查'} |"
        )
    rows.extend(
        [
            "",
            "## 专家复核说明",
            "",
            "原始问答、证据片段、审核意见和分项检查均保存在 `qwen_quality_results.json`。",
            "专家应重点确认：数值是否来自对应工况、机理表述是否越过证据边界、复合材料检测建议是否准确，以及维修输出是否避免越权。",
        ]
    )
    return "\n".join(rows) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="运行 Qwen 真实模型回答质量测评。")
    parser.add_argument("--base-url", default=None, help="保留参数，默认使用进程内 TestClient。")
    args = parser.parse_args()
    payload = run_evaluation(base_url=args.base_url)
    print(json.dumps(payload["metrics"], ensure_ascii=False, indent=2))
    print(f"automated_status={payload['automated_status']}")
    print(f"results={RESULTS_PATH}")


if __name__ == "__main__":
    main()
