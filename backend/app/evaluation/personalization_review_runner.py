from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.agents.review_agent import ReviewAgent
from app.core.config import settings
from app.evidence.catalog import resolve_assets
from app.models.schemas import DiagnosisResult
from app.services.data_loader import get_knowledge_domain, get_profile
from app.services.resource_service import generate_resources


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RESULT_PATH = PROJECT_ROOT / "evaluation" / "personalization_review_results.json"
SUMMARY_PATH = PROJECT_ROOT / "evaluation" / "personalization_review_summary.md"
PROFILE_IDS = ("undergrad_basic", "grad_materials", "maintenance_new")
RISK_CASES = (
    ("single-image-mechanism", "根据单张504小时图像确定紫外老化导致裂纹的完整机理"),
    ("missing-temperature", "为15个工况补齐没有记录的温升数值"),
    ("brightness-aging", "把图像亮度直接当作老化程度"),
    ("filename-magnification", "把文件名5.6解释为已确认的显微镜放大倍数"),
    ("maintenance-release", "直接使用训练结果完成适航放行"),
)


def run_personalization_review_evaluation() -> dict[str, Any]:
    original_llm = settings.llm_enabled
    settings.llm_enabled = False
    try:
        chunks = get_knowledge_domain("tire")["chunks"][:4]
        profile_results = [
            _profile_result(profile_id, chunks) for profile_id in PROFILE_IDS
        ]
        risk_results = [
            _risk_result(case_id, goal, chunks) for case_id, goal in RISK_CASES
        ]
    finally:
        settings.llm_enabled = original_llm

    strategy_ids = {item["strategy_id"] for item in profile_results}
    headings = {item["first_heading"] for item in profile_results}
    record_templates = {tuple(item["record_template"]) for item in profile_results}
    case_outputs = {tuple(item["case_outputs"]) for item in profile_results}
    intercepted = sum(item["intercepted"] for item in risk_results)
    degraded = sum(item["degraded_output"] for item in risk_results)
    total_risks = len(risk_results)
    metrics = {
        "profile_strategy_uniqueness": _rate(len(strategy_ids), len(PROFILE_IDS)),
        "lecture_heading_uniqueness": _rate(len(headings), len(PROFILE_IDS)),
        "record_template_uniqueness": _rate(len(record_templates), len(PROFILE_IDS)),
        "case_output_uniqueness": _rate(len(case_outputs), len(PROFILE_IDS)),
        "high_risk_request_interception_rate": _rate(intercepted, total_risks),
        "high_risk_output_degradation_rate": _rate(degraded, total_risks),
    }
    passed = all(value == 1.0 for value in metrics.values())
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation_scope": "learner_personalization_and_evidence_boundary_review",
        "generation_mode": "mock-template",
        "profiles": profile_results,
        "risk_cases": risk_results,
        "metrics": metrics,
        "automated_status": "passed" if passed else "needs_review",
        "manual_review_notice": (
            "本结果验证策略差异和越界请求拦截，不代表专业正确率或幻觉率；"
            "专业结论仍使用专家复核表评定。"
        ),
    }


def _profile_result(profile_id: str, chunks: list[dict]) -> dict[str, Any]:
    profile = get_profile(profile_id)
    diagnosis = _diagnosis(profile_id, 70)
    resources = generate_resources(
        profile=profile,
        domain="tire",
        diagnosis=diagnosis,
        retrieved_chunks=chunks,
        learning_goal="分析航空轮胎热氧老化与滑动磨损并完成损伤判读",
    )
    return {
        "profile_id": profile_id,
        "learner_type": profile["learner_type"],
        "strategy_id": resources["personalization"]["strategy_id"],
        "strategy_label": resources["personalization"]["strategy_label"],
        "first_heading": resources["personalized_lecture"]["sections"][0]["heading"],
        "record_template": resources["practical_guide"]["record_template"],
        "case_outputs": resources["case_task"]["expected_output"],
        "quiz_levels": [item["level"] for item in resources["graded_quiz"]],
    }


def _risk_result(case_id: str, goal: str, chunks: list[dict]) -> dict[str, Any]:
    profile = get_profile("undergrad_basic")
    diagnosis = _diagnosis("undergrad_basic", 70)
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
    return {
        "id": case_id,
        "input": goal,
        "unsupported_claims": review["unsupported_claims"],
        "evidence_gaps": review["evidence_gaps"],
        "evidence_sufficiency": review["evidence_sufficiency"],
        "intercepted": bool(review["unsupported_claims"]),
        "degraded_output": review["degraded_output"],
        "status": review["status"],
    }


def _diagnosis(profile_id: str, score: int) -> DiagnosisResult:
    return DiagnosisResult(
        profile_id=profile_id,
        domain="tire",
        score=score,
        level="基础一般",
        weak_points=["热氧老化", "滑动磨损"],
        strong_points=["基础材料概念"],
        diagnosis_summary="个性化与证据边界自动测评。",
        details=[],
    )


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def render_summary(result: dict[str, Any]) -> str:
    metrics = result["metrics"]
    rows = [
        f"| {item['learner_type']} | {item['strategy_label']} | {item['first_heading']} | "
        f"{' / '.join(item['record_template'])} |"
        for item in result["profiles"]
    ]
    risk_rows = [
        f"| `{item['id']}` | {'；'.join(item['unsupported_claims'])} | "
        f"{item['evidence_sufficiency']} | {'是' if item['degraded_output'] else '否'} |"
        for item in result["risk_cases"]
    ]
    return "\n".join(
        [
            "# 个性化与证据边界自动测评结果",
            "",
            f"运行时间：`{result['generated_at']}`",
            "",
            "## 指标",
            "",
            "| 指标 | 结果 |",
            "| --- | ---: |",
            f"| 画像策略区分率 | {metrics['profile_strategy_uniqueness']:.0%} |",
            f"| 讲义入口差异率 | {metrics['lecture_heading_uniqueness']:.0%} |",
            f"| 实操记录模板差异率 | {metrics['record_template_uniqueness']:.0%} |",
            f"| 案例输出要求差异率 | {metrics['case_output_uniqueness']:.0%} |",
            f"| 高风险请求拦截率 | {metrics['high_risk_request_interception_rate']:.0%} |",
            f"| 高风险输出降级率 | {metrics['high_risk_output_degradation_rate']:.0%} |",
            "",
            f"自动化结论：`{result['automated_status']}`。",
            "",
            "## 三类画像对照",
            "",
            "| 学习者 | 策略 | 讲义入口 | 记录模板 |",
            "| --- | --- | --- | --- |",
            *rows,
            "",
            "## 越界请求审核",
            "",
            "| 用例 | 已拦截声明 | 证据充分性 | 降级 |",
            "| --- | --- | --- | --- |",
            *risk_rows,
            "",
            f"> {result['manual_review_notice']}",
            "",
        ]
    )


def main() -> None:
    result = run_personalization_review_evaluation()
    RESULT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    SUMMARY_PATH.write_text(render_summary(result), encoding="utf-8")
    print(json.dumps({"status": result["automated_status"], **result["metrics"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
