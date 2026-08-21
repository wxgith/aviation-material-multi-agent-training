from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
EXTERNAL_DIR = ROOT / "evaluation" / "external_review"
PILOT_DIR = ROOT / "evaluation" / "user_pilot"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_blind_cases(qwen_results: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    blind_cases: list[dict[str, Any]] = []
    private_key: list[dict[str, str]] = []
    for index, case in enumerate(qwen_results["cases"], start=1):
        blind_id = f"BLIND-{index:03d}"
        blind_cases.append(
            {
                "blind_case_id": blind_id,
                "learner_profile": case["profile_id"],
                "domain": case["domain"],
                "question": case["question"],
                "answer": case["answer"],
                "explanation_level": case["explanation_level"],
                "evidence_ids": case["evidence_ids"],
                "evidence_titles": case["evidence_titles"],
                "evidence_snippets": case["evidence_snippets"],
                "boundaries": case["boundaries"],
                "follow_up_question": case["follow_up_question"],
                "practice_task": case["practice_task"],
                "review_fields": {
                    "professional_correctness_1_to_5": None,
                    "evidence_consistency_1_to_5": None,
                    "boundary_compliance_1_to_5": None,
                    "difficulty_adaptation_1_to_5": None,
                    "hallucination_flag_0_or_1": None,
                    "verdict": None,
                    "comments": None,
                },
            }
        )
        private_key.append(
            {
                "blind_case_id": blind_id,
                "source_case_id": case["id"],
                "generation_mode": case["generation_mode"],
                "candidate_rejected": str(bool(case["review"].get("candidate_rejected"))).lower(),
                "machine_passed": str(bool(case["machine_passed"])).lower(),
            }
        )
    return blind_cases, private_key


def _write_csv(path: Path, headers: list[str], rows: list[list[Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def build_external_review() -> None:
    EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)
    qwen = _load(ROOT / "evaluation" / "qwen_quality_results.json")
    cases, private_key = build_blind_cases(qwen)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending_external_expert_review",
        "reviewer_visibility": "generation mode, machine result, and ReviewAgent outcome are hidden",
        "case_count": len(cases),
        "cases": cases,
    }
    (EXTERNAL_DIR / "blind_review_cases.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (EXTERNAL_DIR / "blind_case_key_private.json").write_text(
        json.dumps({"do_not_send_to_reviewer": True, "mapping": private_key}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    _write_csv(
        EXTERNAL_DIR / "external_review_scores.csv",
        [
            "blind_case_id",
            "professional_correctness_1_to_5",
            "evidence_consistency_1_to_5",
            "boundary_compliance_1_to_5",
            "difficulty_adaptation_1_to_5",
            "hallucination_flag_0_or_1",
            "verdict_accept_revise_reject",
            "comments",
            "reviewer_name",
            "affiliation_or_title",
            "review_date",
        ],
        [[case["blind_case_id"], "", "", "", "", "", "", "", "", "", ""] for case in cases],
    )


def build_user_pilot() -> None:
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(
        PILOT_DIR / "pilot_participants.csv",
        [
            "anonymous_participant_id",
            "learner_profile",
            "domain",
            "prior_experience_level",
            "consent_confirmed_yes_no",
            "test_date",
            "notes",
        ],
        [[f"P-{index:02d}", "", "", "", "", "", ""] for index in range(1, 10)],
    )
    _write_csv(
        PILOT_DIR / "pilot_task_records.csv",
        [
            "anonymous_participant_id",
            "task_id",
            "task_description",
            "completed_yes_no",
            "completion_time_seconds",
            "error_count",
            "help_request_count",
            "usability_score_1_to_5",
            "comments",
        ],
        [],
    )
    _write_csv(
        PILOT_DIR / "pilot_pre_post_scores.csv",
        [
            "anonymous_participant_id",
            "domain",
            "pre_score_0_to_100",
            "post_score_0_to_100",
            "score_change",
            "knowledge_blind_spots_before",
            "knowledge_blind_spots_after",
            "reviewer_checked_yes_no",
        ],
        [],
    )


def main() -> None:
    build_external_review()
    build_user_pilot()
    print(f"external review package: {EXTERNAL_DIR}")
    print(f"user pilot package: {PILOT_DIR}")


if __name__ == "__main__":
    main()
