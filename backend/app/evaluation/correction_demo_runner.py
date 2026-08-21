"""Run a fixed ReviewAgent rejection, regeneration, and second-review demo."""

from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.agents.orchestrator import orchestrator
from app.core.config import settings
from app.db.database import reset_engine_cache
from app.models.schemas import DiagnosisResult
from app.services.data_loader import get_profile


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_JSON_PATH = PROJECT_ROOT / "evaluation" / "review_correction_demo.json"
DEFAULT_MD_PATH = PROJECT_ROOT / "evaluation" / "review_correction_demo.md"


def run_correction_demo(use_es: bool = False) -> dict[str, Any]:
    original = {
        "database_enabled": settings.database_enabled,
        "data_backend": settings.data_backend,
        "es_enabled": settings.es_enabled,
        "retrieval_mode": settings.retrieval_mode,
        "bge_enabled": settings.bge_enabled,
        "embedding_backend": settings.embedding_backend,
        "llm_enabled": settings.llm_enabled,
    }
    try:
        settings.database_enabled = False
        settings.data_backend = "json"
        settings.es_enabled = use_es
        settings.retrieval_mode = "hybrid"
        settings.bge_enabled = False
        settings.embedding_backend = "none"
        settings.llm_enabled = False
        reset_engine_cache()
        return _execute_demo(use_es)
    finally:
        for key, value in original.items():
            setattr(settings, key, value)
        reset_engine_cache()


def _execute_demo(use_es: bool) -> dict[str, Any]:
    profile = get_profile("undergrad_basic")
    goal = "仅凭单张胎面形貌图确定完整损伤机理，并以训练输出替代适航放行。"
    diagnosis = DiagnosisResult(
        profile_id=profile["profile_id"],
        domain="tire",
        score=40,
        level="基础薄弱",
        weak_points=["热氧老化", "滑动磨损与实验表征方法", "损伤等级判读"],
        strong_points=["常见误区"],
        diagnosis_summary="固定纠偏演示：基础薄弱，并包含越界专业断言请求。",
        details=[],
    )
    context = {
        "profile": profile,
        "domain": "tire",
        "diagnosis_result": diagnosis,
        "learning_goal": goal,
    }
    orchestrator.diagnosis_agent.run(context)
    orchestrator.router_agent.run(context)
    retrieval_step = orchestrator.retrieval_agent.run(context)
    generation_step = orchestrator.generation_agent.run(context)

    draft = context["resources"]
    draft["personalized_lecture"]["sections"][0]["evidence_ids"] = ["fabricated-evidence-001"]
    draft["practical_guide"]["constraints"] = []
    draft["practical_guide"]["evidence_ids"] = []
    draft["case_task"]["evidence_ids"] = []
    submitted_draft = _resource_snapshot(draft)

    first_review_step = orchestrator.review_agent.run(context)
    initial_review = copy.deepcopy(context["review"])
    if not initial_review.get("requires_regeneration"):
        raise RuntimeError("固定案例未触发审核驳回")

    context["review_retry"] = True
    context["correction_guidance"] = initial_review["rejection_reasons"]
    corrected_generation_step = orchestrator.generation_agent.run(context)
    corrected_resources = _resource_snapshot(context["resources"])
    final_review_step = orchestrator.review_agent.run(context)
    context["review"]["correction_rounds"] = 1
    context["review"]["initial_review"] = initial_review
    final_review_step.details = context["review"]
    decision_step = orchestrator.decision_agent.run(context)
    final_review = context["review"]

    assertions = {
        "initial_review_rejected": initial_review["requires_regeneration"] and not initial_review["approved"],
        "fabricated_evidence_detected": any(
            "fabricated-evidence-001" in item for item in initial_review["rejection_reasons"]
        ),
        "missing_constraints_detected": any(
            "安全约束" in item for item in initial_review["rejection_reasons"]
        ),
        "high_risk_claim_degraded": bool(initial_review["unsupported_claims"]),
        "corrected_evidence_bound": "fabricated-evidence-001" not in json.dumps(corrected_resources, ensure_ascii=False),
        "corrected_constraints_restored": corrected_resources["constraint_count"] > 0,
        "second_review_approved": final_review["approved"] and not final_review["requires_regeneration"],
        "correction_round_recorded": final_review["correction_rounds"] == 1,
    }
    if not all(assertions.values()):
        raise RuntimeError(f"纠偏案例验证失败：{assertions}")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_id": "review-reject-regenerate-001",
        "title": "单图确定机理与越权放行请求的审核驳回—纠偏重生案例",
        "runtime_mode": {
            "database_enabled": False,
            "es_enabled": use_es,
            "llm_enabled": False,
        },
        "learner_profile": profile,
        "diagnosis": diagnosis.model_dump(),
        "learning_goal": goal,
        "retrieval": {
            "knowledge_source": context.get("retrieval_source"),
            "retrieval_mode": context.get("retrieval_mode"),
            "evidence_ids": retrieval_step.evidence_ids,
        },
        "submitted_draft": submitted_draft,
        "faults": [
            "注入未检索证据 fabricated-evidence-001",
            "移除实操指南边界条件与安全约束",
            "请求由单图确定完整机理并替代适航放行",
        ],
        "initial_review": initial_review,
        "correction_guidance": initial_review["rejection_reasons"],
        "corrected_generation": {
            "step_summary": corrected_generation_step.output_summary,
            "resources": corrected_resources,
            "correction_applied": context["resources"].get("review_correction_applied", []),
        },
        "final_review": final_review,
        "decision": context["decision"],
        "agent_step_summaries": [
            generation_step.output_summary,
            first_review_step.output_summary,
            corrected_generation_step.output_summary,
            final_review_step.output_summary,
            decision_step.output_summary,
        ],
        "assertions": assertions,
        "status": "passed",
        "boundary_notice": "该案例使用显式故障注入验证审核闭环，不代表正常生成会主动产生这些错误。",
    }


def _resource_snapshot(resources: dict[str, Any]) -> dict[str, Any]:
    lecture_ids = [
        evidence_id
        for section in resources["personalized_lecture"]["sections"]
        for evidence_id in section.get("evidence_ids", [])
    ]
    return {
        "difficulty": resources["difficulty_match"]["resource_difficulty"],
        "lecture_evidence_ids": lecture_ids,
        "practical_evidence_ids": resources["practical_guide"].get("evidence_ids", []),
        "case_evidence_ids": resources["case_task"].get("evidence_ids", []),
        "constraint_count": len(resources["practical_guide"].get("constraints", [])),
        "quiz_explanations_complete": all(
            bool(item.get("explanation")) for item in resources.get("graded_quiz", [])
        ),
    }


def render_markdown(result: dict[str, Any]) -> str:
    initial = result["initial_review"]
    final = result["final_review"]
    assertion_rows = [
        f"| {name} | {'通过' if passed else '失败'} |"
        for name, passed in result["assertions"].items()
    ]
    return "\n".join(
        [
            "# 审核驳回—纠偏重生固定案例",
            "",
            f"案例：`{result['case_id']}`",
            "",
            f"学习目标：{result['learning_goal']}",
            "",
            "> 本案例通过显式故障注入验证审核闭环，不表示正常资源会主动生成这些错误。",
            "",
            "## 1. 提交审核的故障草案",
            "",
            *[f"- {item}" for item in result["faults"]],
            "",
            f"- 草案约束数量：{result['submitted_draft']['constraint_count']}",
            f"- 草案讲义证据：{result['submitted_draft']['lecture_evidence_ids']}",
            "",
            "## 2. 首次审核：驳回",
            "",
            f"- 状态：{initial['status']}",
            f"- `requires_regeneration`：{initial['requires_regeneration']}",
            f"- 阻断原因：{'；'.join(initial['rejection_reasons'])}",
            f"- 越界声明：{'；'.join(initial['unsupported_claims'])}",
            "",
            "## 3. 纠偏重生",
            "",
            f"- 纠偏指令：{'；'.join(result['correction_guidance'])}",
            f"- 重生后约束数量：{result['corrected_generation']['resources']['constraint_count']}",
            f"- 重生后讲义证据：{result['corrected_generation']['resources']['lecture_evidence_ids']}",
            "",
            "## 4. 二次审核：按边界通过",
            "",
            f"- 状态：{final['status']}",
            f"- `approved`：{final['approved']}",
            f"- 纠偏轮次：{final['correction_rounds']}",
            f"- 降级说明：{final['degradation_notice']}",
            "",
            "## 5. 自动断言",
            "",
            "| 断言 | 结果 |",
            "| --- | --- |",
            *assertion_rows,
            "",
            f"最终结果：`{result['status']}`。",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--use-es", action="store_true")
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_PATH)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD_PATH)
    args = parser.parse_args()
    result = run_correction_demo(use_es=args.use_es)
    args.json_output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    args.markdown_output.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({"case_id": result["case_id"], "status": result["status"], "assertions": result["assertions"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
