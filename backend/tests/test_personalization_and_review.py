from app.agents.review_agent import ReviewAgent
from app.evidence.catalog import resolve_assets
from app.models.schemas import DiagnosisResult
from app.services.data_loader import get_knowledge_domain, get_profile
from app.services.resource_service import _join_chunk_contents, generate_resources


def _diagnosis(profile_id: str, score: int = 70) -> DiagnosisResult:
    return DiagnosisResult(
        profile_id=profile_id,
        domain="tire",
        score=score,
        level="基础一般",
        weak_points=["热氧老化", "滑动磨损"],
        strong_points=["基础材料概念"],
        diagnosis_summary="用于个性化与审核回归测试。",
        details=[],
    )


def _resources(profile_id: str, learning_goal: str = "分析航空轮胎损伤") -> dict:
    profile = get_profile(profile_id)
    diagnosis = _diagnosis(profile_id)
    chunks = get_knowledge_domain("tire")["chunks"][:4]
    return generate_resources(
        profile=profile,
        domain="tire",
        diagnosis=diagnosis,
        retrieved_chunks=chunks,
        learning_goal=learning_goal,
    )


def test_three_learner_profiles_generate_materially_different_resources():
    undergraduate = _resources("undergrad_basic")
    graduate = _resources("grad_materials")
    maintenance = _resources("maintenance_new")

    strategies = {
        undergraduate["personalization"]["strategy_id"],
        graduate["personalization"]["strategy_id"],
        maintenance["personalization"]["strategy_id"],
    }
    headings = {
        undergraduate["personalized_lecture"]["sections"][0]["heading"],
        graduate["personalized_lecture"]["sections"][0]["heading"],
        maintenance["personalized_lecture"]["sections"][0]["heading"],
    }
    record_templates = {
        tuple(undergraduate["practical_guide"]["record_template"]),
        tuple(graduate["practical_guide"]["record_template"]),
        tuple(maintenance["practical_guide"]["record_template"]),
    }
    case_outputs = {
        tuple(undergraduate["case_task"]["expected_output"]),
        tuple(graduate["case_task"]["expected_output"]),
        tuple(maintenance["case_task"]["expected_output"]),
    }

    assert strategies == {"undergraduate", "graduate", "maintenance"}
    assert len(headings) == 3
    assert len(record_templates) == 3
    assert len(case_outputs) == 3
    assert "可观察" in undergraduate["personalization"]["explanation_style"]
    assert "变量控制" in graduate["personalization"]["explanation_style"]
    assert "升级报告" in maintenance["personalization"]["explanation_style"]
    assert graduate["graded_quiz"][-1]["level"] == "进阶"
    assert maintenance["graded_quiz"][-1]["level"] == "情景决策"
    evidence_summary = _join_chunk_contents([
        {
            "id": "duplicate-a",
            "title": "耦合损伤边界",
            "content": "耦合损伤边界需要结合老化时间、摩擦载荷和滑动距离综合判断。",
        },
        {
            "id": "duplicate-b",
            "title": "耦合损伤边界补充",
            "content": "耦合损伤边界应结合老化时间、摩擦载荷和滑动距离进行综合判断。",
        },
        {
            "id": "table-evidence",
            "title": "Aging conditions",
            "content": (
                "| aging_condition_id | set_temperature_C | duration_h | atmosphere | qc_flag |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| AGE-24H | 75 | 24 | air | pass |"
            ),
        },
    ])
    assert "| --- |" not in evidence_summary
    assert "老化条件编号" in evidence_summary
    assert evidence_summary.count("耦合损伤边界") == 1


def test_review_agent_degrades_single_image_mechanism_claim():
    profile = get_profile("undergrad_basic")
    diagnosis = _diagnosis("undergrad_basic")
    chunks = get_knowledge_domain("tire")["chunks"][:4]
    resources = generate_resources(
        profile=profile,
        domain="tire",
        diagnosis=diagnosis,
        retrieved_chunks=chunks,
        learning_goal="根据单张504小时图像确定紫外老化导致裂纹的完整机理",
    )
    assets = resolve_assets(
        query_text="根据单张504小时图像确定紫外老化导致裂纹的完整机理",
        limit=8,
    )
    context = {
        "resources": resources,
        "retrieved_chunks": chunks,
        "diagnosis_result": diagnosis,
        "learning_goal": "根据单张504小时图像确定紫外老化导致裂纹的完整机理",
        "experimental_evidence": assets[:1],
    }

    step = ReviewAgent().run(context)
    review = context["review"]

    assert step.status == "completed"
    assert review["approved"] is True
    assert review["degraded_output"] is True
    assert review["evidence_sufficiency"] == "limited"
    assert "由单一图像确定完整机理或整体分布" in review["unsupported_claims"]
    assert any(item["status"] == "degraded-hypothesis" for item in review["claim_assessments"])
    assert "专业机理正确性" in review["review_scope"]["expert_review_required"]


def test_review_agent_rejects_fabricated_temperature_values():
    profile = get_profile("grad_materials")
    diagnosis = _diagnosis("grad_materials", score=82)
    chunks = get_knowledge_domain("tire")["chunks"][:4]
    goal = "为15个工况补齐没有记录的温升数值"
    resources = generate_resources(
        profile=profile,
        domain="tire",
        diagnosis=diagnosis,
        retrieved_chunks=chunks,
        learning_goal=goal,
    )
    context = {
        "resources": resources,
        "retrieved_chunks": chunks,
        "diagnosis_result": diagnosis,
        "learning_goal": goal,
        "experimental_evidence": resolve_assets(query_text=goal, limit=8),
    }

    ReviewAgent().run(context)
    review = context["review"]

    assert "补齐未记录的实验参数或温升数值" in review["unsupported_claims"]
    assert review["degraded_output"] is True
    assert any(
        "缺失参数保持未知，不进行插补" in item["boundary"]
        for item in review["claim_assessments"]
    )


def test_review_agent_marks_condition_bound_training_evidence_as_sufficient():
    profile = get_profile("grad_materials")
    diagnosis = _diagnosis("grad_materials", score=82)
    chunks = get_knowledge_domain("tire")["chunks"][:4]
    goal = "比较80米时40、50、60 N磨损形貌并说明变量控制"
    resources = generate_resources(
        profile=profile,
        domain="tire",
        diagnosis=diagnosis,
        retrieved_chunks=chunks,
        learning_goal=goal,
    )
    context = {
        "resources": resources,
        "retrieved_chunks": chunks,
        "diagnosis_result": diagnosis,
        "learning_goal": goal,
        "experimental_evidence": resolve_assets(query_text=goal, limit=8),
    }

    ReviewAgent().run(context)
    review = context["review"]

    assert review["evidence_sufficiency"] == "sufficient_for_training"
    assert review["degraded_output"] is False
    assert review["unsupported_claims"] == []
    assert "实验资产工况字段可追溯" in review["verified_claims"]
    assert "专家复核" in review["consistency_check"]


def test_personalization_review_evaluation_passes():
    from app.evaluation.personalization_review_runner import (
        run_personalization_review_evaluation,
    )

    result = run_personalization_review_evaluation()

    assert result["automated_status"] == "passed"
    assert result["metrics"]["profile_strategy_uniqueness"] == 1.0
    assert result["metrics"]["high_risk_request_interception_rate"] == 1.0
    assert result["metrics"]["high_risk_output_degradation_rate"] == 1.0


def test_review_agent_rejects_resources_without_evidence_bindings():
    profile = get_profile("undergrad_basic")
    diagnosis = _diagnosis("undergrad_basic", score=40)
    chunks = get_knowledge_domain("tire")["chunks"][:4]
    resources = generate_resources(
        profile=profile,
        domain="tire",
        diagnosis=diagnosis,
        retrieved_chunks=chunks,
        learning_goal="完成航空轮胎胎面损伤基础判读",
    )
    for section in resources["personalized_lecture"]["sections"]:
        section["evidence_ids"] = []
    resources["practical_guide"]["evidence_ids"] = []
    resources["case_task"]["evidence_ids"] = []
    context = {
        "resources": resources,
        "retrieved_chunks": chunks,
        "diagnosis_result": diagnosis,
        "learning_goal": "完成航空轮胎胎面损伤基础判读",
        "experimental_evidence": [],
    }

    ReviewAgent().run(context)
    review = context["review"]

    assert review["approved"] is False
    assert review["requires_regeneration"] is True
    assert "生成资源缺少 evidence_ids 绑定，无法完成知识溯源" in review["rejection_reasons"]


def test_review_rejection_regeneration_demo_passes():
    from app.evaluation.correction_demo_runner import run_correction_demo

    result = run_correction_demo(use_es=False)

    assert result["status"] == "passed"
    assert result["initial_review"]["requires_regeneration"] is True
    assert result["final_review"]["approved"] is True
    assert result["final_review"]["correction_rounds"] == 1
    assert all(result["assertions"].values())
