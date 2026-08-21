from app.evaluation.review_gate_ablation import build_ablation


def test_review_gate_ablation_reports_paired_interventions():
    qwen = {
        "cases": [
            {
                "id": "accepted",
                "domain": "tire",
                "profile_id": "undergrad_basic",
                "question": "explain",
                "generation_mode": "llm",
                "generation_audit": {"outcome": "success"},
                "review": {"candidate_rejected": False, "risk_points": [], "corrections": []},
                "checks": {"evidence_closed": True, "review_controlled": True},
                "machine_passed": True,
                "retrieval_mode": "hybrid",
                "knowledge_source": "elasticsearch",
            },
            {
                "id": "rejected",
                "domain": "composite",
                "profile_id": "grad_materials",
                "question": "classify",
                "generation_mode": "review-template-fallback",
                "generation_audit": {
                    "outcome": "review_fallback",
                    "candidate_generation_audit": {"outcome": "success"},
                },
                "review": {
                    "candidate_rejected": True,
                    "risk_points": ["unsupported claim"],
                    "corrections": ["remove claim"],
                },
                "checks": {"evidence_closed": True, "review_controlled": True},
                "machine_passed": True,
                "retrieval_mode": "hybrid",
                "knowledge_source": "elasticsearch",
            },
        ]
    }
    full = {
        "metrics": {
            "executed_cases": 50,
            "passed_cases": 50,
            "agent_completeness_rate": 1.0,
            "correction_cases": 8,
            "core_key_point_proxy_coverage": 0.9727,
            "difficulty_rule_match_accuracy": 0.96,
            "unresolved_claim_risk_proxy_rate": 0.0,
        }
    }

    result = build_ablation(qwen, full)

    paired = result["paired_cohort"]
    assert paired["case_count"] == 2
    assert paired["direct_candidate_passed"] == 1
    assert paired["review_gate_interventions"] == 1
    assert paired["post_gate_machine_passed"] == 2
    assert paired["acceptance_improvement_points"] == 50.0
    assert result["network_or_llm_called"] is False
