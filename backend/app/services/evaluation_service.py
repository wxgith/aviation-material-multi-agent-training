"""Read-only competition evaluation summaries for API and UI display."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EVALUATION_DIR = PROJECT_ROOT / "evaluation"
EXECUTION_RESULT_PATH = EVALUATION_DIR / "full_case_execution_results.json"
EXPERT_CONFIRMATION_PATH = EVALUATION_DIR / "expert_review_confirmation.json"
GUIDED_INQUIRY_RESULT_PATH = EVALUATION_DIR / "guided_inquiry_results.json"


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def get_evaluation_summary() -> dict[str, Any]:
    execution = _load_json(EXECUTION_RESULT_PATH) or {}
    confirmation = _load_json(EXPERT_CONFIRMATION_PATH) or {}
    guided_inquiry = _load_json(GUIDED_INQUIRY_RESULT_PATH) or {}
    machine_metrics = execution.get("metrics", {})
    expert_metrics = confirmation.get("metrics", {})
    guided_metrics = guided_inquiry.get("metrics", {})
    total_cases = int(machine_metrics.get("executed_cases", 0))
    passed_cases = int(machine_metrics.get("passed_cases", 0))
    expert_status = confirmation.get("expert_review_status", "pending_expert_review")
    return {
        "status": "passed" if (
            total_cases
            and passed_cases == total_cases
            and guided_metrics.get("case_count")
            and guided_metrics.get("passed_cases") == guided_metrics.get("case_count")
        ) else "pending",
        "generated_at": confirmation.get("generated_at") or execution.get("generated_at"),
        "core_cases": {
            "total": total_cases,
            "passed": passed_cases,
            "pass_rate": machine_metrics.get("execution_pass_rate", 0.0),
        },
        "machine_assisted_metrics": {
            "agent_completeness_rate": machine_metrics.get("agent_completeness_rate", 0.0),
            "core_key_point_proxy_coverage": machine_metrics.get("core_key_point_proxy_coverage", 0.0),
            "difficulty_rule_match_accuracy": machine_metrics.get("difficulty_rule_match_accuracy", 0.0),
            "feedback_decision_accuracy": machine_metrics.get("feedback_decision_accuracy", 0.0),
            "correction_cases": machine_metrics.get("correction_cases", 0),
        },
        "guided_inquiry": {
            "total": guided_metrics.get("case_count", 0),
            "passed": guided_metrics.get("passed_cases", 0),
            "pass_rate": guided_metrics.get("pass_rate", 0.0),
            "agent_completeness_rate": guided_metrics.get("agent_completeness_rate", 0.0),
            "evidence_closure_rate": guided_metrics.get("evidence_closure_rate", 0.0),
            "personalization_match_rate": guided_metrics.get("personalization_match_rate", 0.0),
            "decision_accuracy": guided_metrics.get("decision_accuracy", 0.0),
            "security_control_rate": guided_metrics.get("security_control_rate", 0.0),
            "elasticsearch_usage_rate": guided_metrics.get("elasticsearch_usage_rate", 0.0),
            "mode": guided_inquiry.get("mode", "not-run"),
        },
        "expert_review": {
            "status": expert_status,
            "confirmed": expert_status == "confirmed_accurate",
            "professional_accuracy": expert_metrics.get("professional_accuracy"),
            "core_knowledge_point_coverage": expert_metrics.get("core_knowledge_point_coverage"),
            "hallucination_rate": expert_metrics.get("hallucination_rate"),
            "difficulty_adaptation_accuracy": expert_metrics.get("difficulty_adaptation_accuracy"),
            "signature_status": confirmation.get(
                "reviewer_signature_status", "pending_identity_and_signature"
            ),
            "submission_notice": confirmation.get("submission_notice"),
        },
        "evidence_files": {
            "execution_status": "evaluation/full_case_execution_status.md",
            "expert_confirmation": "evaluation/expert_review_confirmation.md",
            "correction_demo": "evaluation/review_correction_demo.md",
            "guided_inquiry": "evaluation/guided_inquiry_summary.md",
        },
    }
