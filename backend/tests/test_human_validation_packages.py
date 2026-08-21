from app.evaluation.human_validation_packages import build_blind_cases


def test_blind_cases_hide_generation_and_review_outcomes():
    qwen = {
        "cases": [
            {
                "id": "source-1",
                "profile_id": "undergrad_basic",
                "domain": "tire",
                "question": "question",
                "answer": "answer",
                "explanation_level": "basic",
                "evidence_ids": ["tire-k01"],
                "evidence_titles": ["title"],
                "evidence_snippets": [{"evidence_id": "tire-k01", "snippet": "text"}],
                "boundaries": ["boundary"],
                "follow_up_question": "follow-up",
                "practice_task": "task",
                "generation_mode": "review-template-fallback",
                "review": {"candidate_rejected": True},
                "machine_passed": True,
            }
        ]
    }

    cases, private_key = build_blind_cases(qwen)

    assert cases[0]["blind_case_id"] == "BLIND-001"
    assert "generation_mode" not in cases[0]
    assert "candidate_rejected" not in cases[0]
    assert private_key[0]["source_case_id"] == "source-1"
    assert private_key[0]["candidate_rejected"] == "true"
