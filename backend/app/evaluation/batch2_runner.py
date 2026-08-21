from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.agents.orchestrator import orchestrator
from app.core.config import settings
from app.db.database import reset_engine_cache
from app.models.schemas import AgentRunRequest, DiagnosisResult
from app.services.data_loader import load_profiles
from app.services.report_service import _feedback_action


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EVALUATION_DIR = PROJECT_ROOT / "evaluation"
CASES_PATH = EVALUATION_DIR / "team_experiment_eval_cases_batch2.json"
CATALOG_PATH = PROJECT_ROOT / "knowledge_corpus" / "experimental_assets" / "catalog.json"
RESULTS_PATH = EVALUATION_DIR / "batch2_automated_results.json"
SUMMARY_PATH = EVALUATION_DIR / "batch2_evaluation_summary.md"
EXPERT_TASKS_PATH = EVALUATION_DIR / "batch2_expert_review_tasks.md"
ASSET_CHECKLIST_PATH = EVALUATION_DIR / "batch2_asset_verification_checklist.md"

REQUIRED_FIELDS = {
    "id",
    "test_type",
    "learner_profile",
    "domain",
    "input",
    "expected_key_points",
    "expected_asset_ids",
    "expected_agent_steps",
    "expected_next_action",
    "pass_criteria",
}
RESOURCE_KEYS = ("personalized_lecture", "practical_guide", "graded_quiz", "case_task")


def run_batch2_evaluation() -> dict[str, Any]:
    payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    cases = payload["cases"]
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    assets = {item["asset_id"]: item for item in catalog["assets"]}
    dataset = validate_batch2_dataset(cases, assets)

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
        settings.retrieval_mode = "hybrid"
        settings.bge_enabled = False
        settings.embedding_backend = "none"
        settings.llm_enabled = False
        reset_engine_cache()
        case_results = [_evaluate_case(case) for case in cases]
    finally:
        for key, value in original.items():
            setattr(settings, key, value)
        reset_engine_cache()

    metrics = _calculate_metrics(cases, case_results, assets)
    automated_passed = (
        dataset["passed"]
        and metrics["retrieval_case_hit_rate"] >= 0.8
        and metrics["agent_completeness_rate"] == 1.0
        and metrics["resource_structure_completeness_rate"] == 1.0
        and metrics["evidence_traceability_rate"] == 1.0
        and metrics["feedback_decision_accuracy"] == 1.0
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation_scope": "batch2_uv_and_load_distance_experimental_evidence",
        "runtime_mode": {
            "data_backend": "json",
            "database_writes": False,
            "es_enabled": original["es_enabled"],
            "retrieval_mode": "hybrid",
            "bge_enabled": False,
            "llm_enabled": False,
        },
        "dataset": dataset,
        "metrics": metrics,
        "cases": case_results,
        "automated_status": "passed" if automated_passed else "needs_review",
        "manual_review_status": "pending_expert_review",
        "manual_metrics_pending": [
            "专业正确率",
            "核心知识点语义覆盖率",
            "幻觉率",
            "难度适配准确率",
            "形貌观察与机理推断边界",
            "实验参数和样品映射复核",
        ],
    }


def validate_batch2_dataset(cases: list[dict], assets: dict[str, dict]) -> dict[str, Any]:
    missing_fields = {
        case.get("id", f"row-{index}"): sorted(REQUIRED_FIELDS - set(case))
        for index, case in enumerate(cases)
        if REQUIRED_FIELDS - set(case)
    }
    duplicate_ids = sorted(
        key for key, count in Counter(case.get("id") for case in cases).items() if count > 1
    )
    missing_assets = {
        case["id"]: sorted(set(case.get("expected_asset_ids", [])) - set(assets))
        for case in cases
        if set(case.get("expected_asset_ids", [])) - set(assets)
    }
    invalid_steps = [case["id"] for case in cases if len(case.get("expected_agent_steps", [])) != 6]
    return {
        "passed": (
            len(cases) == 20
            and not missing_fields
            and not duplicate_ids
            and not missing_assets
            and not invalid_steps
        ),
        "total_cases": len(cases),
        "type_counts": dict(sorted(Counter(case["test_type"] for case in cases).items())),
        "missing_fields": missing_fields,
        "duplicate_ids": duplicate_ids,
        "missing_asset_references": missing_assets,
        "invalid_agent_step_cases": invalid_steps,
    }


def _evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    profile_id = _profile_id(case["learner_profile"])
    score = _score_from_case(case)
    diagnosis = DiagnosisResult(
        profile_id=profile_id,
        domain=case["domain"],
        score=score,
        level="基础一般" if score < 75 else "掌握较好",
        weak_points=case["expected_key_points"],
        strong_points=[],
        diagnosis_summary="第二批实验依据量化测评输入。",
        details=[],
    )
    session = orchestrator.run(
        AgentRunRequest(
            profile_id=profile_id,
            domain=case["domain"],
            diagnosis_result=diagnosis,
            learning_goal=case["input"],
        )
    )
    steps = session["agent_steps"]
    retrieval_step = next(step for step in steps if "retrieval_mode" in step.details)
    evidence_assets = retrieval_step.details.get("experimental_evidence", [])
    actual_asset_ids = [item["asset_id"] for item in evidence_assets]
    expected_asset_ids = case["expected_asset_ids"]
    matched_asset_ids = sorted(set(actual_asset_ids) & set(expected_asset_ids))
    serialized_resources = json.dumps(session["resources"], ensure_ascii=False).lower()
    matched_key_points = [
        point for point in case["expected_key_points"] if point.lower() in serialized_resources
    ]
    feedback_result = None
    score_match = re.search(r"(\d+)%", case["input"])
    if "反馈" in case["test_type"] and score_match:
        feedback_score = int(score_match.group(1))
        actual_action, explanation = _feedback_action(feedback_score, "")
        feedback_result = {
            "score": feedback_score,
            "expected_action": case["expected_next_action"],
            "actual_action": actual_action,
            "explanation": explanation,
            "passed": actual_action == case["expected_next_action"],
        }
    return {
        "id": case["id"],
        "test_type": case["test_type"],
        "input": case["input"],
        "expected_asset_ids": expected_asset_ids,
        "actual_asset_ids": actual_asset_ids,
        "matched_asset_ids": matched_asset_ids,
        "asset_hit": bool(matched_asset_ids),
        "expected_key_points": case["expected_key_points"],
        "matched_key_points_by_literal_check": matched_key_points,
        "literal_key_point_coverage": round(
            len(matched_key_points) / len(case["expected_key_points"]), 4
        ) if case["expected_key_points"] else 1.0,
        "agent_step_count": len(steps),
        "agent_steps": [step.agent_name for step in steps],
        "agent_complete": len(steps) == 6,
        "resources_complete": all(session["resources"].get(key) for key in RESOURCE_KEYS),
        "review_structure_complete": bool(session["review"].get("risk_points"))
        and bool(session["review"].get("evidence_ids")),
        "review_status": session["review"].get("status"),
        "review_risk_points": session["review"].get("risk_points", []),
        "recommended_action": session["decision"].get("recommended_action"),
        "retrieval_source": retrieval_step.details.get("knowledge_source"),
        "effective_retrieval_mode": retrieval_step.details.get("effective_retrieval_mode"),
        "retrieval_evidence_ids": retrieval_step.details.get("evidence_ids", []),
        "feedback": feedback_result,
    }


def _calculate_metrics(
    cases: list[dict], results: list[dict], assets: dict[str, dict]
) -> dict[str, Any]:
    total = len(results)
    expected_references = sum(len(item["expected_asset_ids"]) for item in results)
    matched_references = sum(len(item["matched_asset_ids"]) for item in results)
    actual_assets = {
        asset_id for result in results for asset_id in result["actual_asset_ids"] if asset_id in assets
    }
    traceable_assets = {
        asset_id
        for asset_id in actual_assets
        if assets[asset_id].get("source_sha256")
        and assets[asset_id].get("derived_sha256")
        and assets[asset_id].get("source_reference")
        and assets[asset_id].get("limitations")
    }
    feedback_results = [item["feedback"] for item in results if item["feedback"] is not None]
    feedback_passed = sum(item["passed"] for item in feedback_results)
    return {
        "retrieval_case_hits": sum(item["asset_hit"] for item in results),
        "retrieval_case_total": total,
        "retrieval_case_hit_rate": _rate(sum(item["asset_hit"] for item in results), total),
        "expected_asset_reference_recall": _rate(matched_references, expected_references),
        "matched_asset_references": matched_references,
        "expected_asset_references": expected_references,
        "agent_completeness_rate": _rate(sum(item["agent_complete"] for item in results), total),
        "resource_structure_completeness_rate": _rate(
            sum(item["resources_complete"] for item in results), total
        ),
        "review_structure_completeness_rate": _rate(
            sum(item["review_structure_complete"] for item in results), total
        ),
        "literal_key_point_coverage": round(
            sum(item["literal_key_point_coverage"] for item in results) / total, 4
        ) if total else 0.0,
        "evidence_traceability_rate": _rate(len(traceable_assets), len(actual_assets)),
        "traceable_assets": len(traceable_assets),
        "actual_assets_examined": len(actual_assets),
        "feedback_decision_accuracy": _rate(feedback_passed, len(feedback_results)),
        "feedback_cases_automated": len(feedback_results),
        "knowledge_sources": dict(Counter(item["retrieval_source"] for item in results)),
        "effective_retrieval_modes": dict(
            Counter(item["effective_retrieval_mode"] for item in results)
        ),
        "professional_accuracy": "pending_expert_review",
        "hallucination_rate": "pending_expert_review",
        "difficulty_adaptation_accuracy": "pending_expert_review",
    }


def render_summary(result: dict[str, Any]) -> str:
    metrics = result["metrics"]
    failed = [item for item in result["cases"] if not item["asset_hit"]]
    failed_rows = [
        f"| `{item['id']}` | {', '.join(item['expected_asset_ids'])} | "
        f"{', '.join(item['actual_asset_ids']) or '无'} |"
        for item in failed
    ] or ["| 无 | - | - |"]
    return "\n".join(
        [
            "# 第二批实验依据量化评测结果",
            "",
            f"运行时间：`{result['generated_at']}`",
            "",
            "## 自动化指标",
            "",
            "| 指标 | 结果 | 状态 |",
            "| --- | ---: | --- |",
            f"| 测评集结构完整性 | {result['dataset']['total_cases']}/20 | {'通过' if result['dataset']['passed'] else '待修复'} |",
            f"| 实验资产检索用例命中率 | {metrics['retrieval_case_hit_rate']:.1%} | {'通过' if metrics['retrieval_case_hit_rate'] >= .8 else '待优化'} |",
            f"| 期望资产引用召回率 | {metrics['expected_asset_reference_recall']:.1%} | 诊断指标 |",
            f"| Agent 完整率 | {metrics['agent_completeness_rate']:.1%} | {'通过' if metrics['agent_completeness_rate'] == 1 else '待修复'} |",
            f"| 四类资源结构完整率 | {metrics['resource_structure_completeness_rate']:.1%} | {'通过' if metrics['resource_structure_completeness_rate'] == 1 else '待修复'} |",
            f"| 审核结构完整率 | {metrics['review_structure_completeness_rate']:.1%} | {'通过' if metrics['review_structure_completeness_rate'] == 1 else '待修复'} |",
            f"| 实验资产可追溯率 | {metrics['evidence_traceability_rate']:.1%} | {'通过' if metrics['evidence_traceability_rate'] == 1 else '待修复'} |",
            f"| 反馈决策准确率 | {metrics['feedback_decision_accuracy']:.1%} | {'通过' if metrics['feedback_decision_accuracy'] == 1 else '待修复'} |",
            f"| 字面关键点覆盖率 | {metrics['literal_key_point_coverage']:.1%} | 仅作机器筛查 |",
            "",
            f"自动化结论：`{result['automated_status']}`。专家复核状态：`{result['manual_review_status']}`。",
            "",
            "> 字面关键点覆盖率不能代替语义覆盖率；专业正确率、幻觉率和难度适配准确率必须由专家填写复核表后计算。",
            "",
            "## 未命中用例",
            "",
            "| 用例 | 期望资产 | 实际资产 |",
            "| --- | --- | --- |",
            *failed_rows,
            "",
            "## 待人工给出的正式指标",
            "",
            "- 专业正确率；",
            "- 核心知识点语义覆盖率；",
            "- 幻觉率；",
            "- 难度适配准确率；",
            "- 形貌观察与机理推断边界合规率；",
            "- 紫外摩擦参数和载荷-距离样品映射复核结论。",
            "",
        ]
    )


def render_expert_tasks(result: dict[str, Any], case_map: dict[str, dict]) -> str:
    lines = [
        "# 第二批专家逐条复核任务",
        "",
        "请领域专家结合系统输出、实验资产图像、工况字段和原始记录逐条评分。自动命中不代表专业结论正确。",
        "",
        "## 评分规则",
        "",
        "- 专业正确性、证据一致性、难度适配、实操约束均按1-5分填写。",
        "- 幻觉条数：记录无证据支持、与证据冲突或越过实验边界的独立陈述数量。",
        "- 通过建议：专业正确性和证据一致性均不低于4分，且严重幻觉为0。",
        "",
    ]
    for index, item in enumerate(result["cases"], start=1):
        case = case_map[item["id"]]
        lines.extend(
            [
                f"## {index}. `{item['id']}`｜{item['test_type']}",
                "",
                f"- 学习者：{case['learner_profile']}",
                f"- 输入：{case['input']}",
                f"- 预期关键点：{'；'.join(case['expected_key_points'])}",
                f"- 预期资产：{', '.join(case['expected_asset_ids'])}",
                f"- 实际资产：{', '.join(item['actual_asset_ids']) or '无'}",
                f"- 检索来源：{item['retrieval_source']} / {item['effective_retrieval_mode']}",
                f"- 自动资产命中：{'是' if item['asset_hit'] else '否'}",
                f"- 自动字面关键点覆盖：{item['literal_key_point_coverage']:.0%}",
                "",
                "| 复核项 | 专家填写 |",
                "| --- | --- |",
                "| 专业正确性（1-5） |  |",
                "| 证据一致性（1-5） |  |",
                "| 难度适配（1-5） |  |",
                "| 实操约束完整性（1-5） |  |",
                "| 观察事实与机理推断是否分离（是/否） |  |",
                "| 工况参数与样品映射是否正确（是/否/不适用） |  |",
                "| 幻觉条数 |  |",
                "| 严重幻觉条数 |  |",
                "| 结论（通过/修改后通过/不通过） |  |",
                "| 问题定位与修改建议 |  |",
                "",
            ]
        )
    lines.extend(
        [
            "## 汇总签字",
            "",
            "| 项目 | 填写 |",
            "| --- | --- |",
            "| 完成复核用例数 |  |",
            "| 专业正确率 |  |",
            "| 核心知识点语义覆盖率 |  |",
            "| 幻觉率 |  |",
            "| 难度适配准确率 |  |",
            "| 证据一致性通过率 |  |",
            "| 专家姓名与职称 |  |",
            "| 复核日期 |  |",
            "| 签字 |  |",
            "",
        ]
    )
    return "\n".join(lines)


def render_asset_checklist(assets: dict[str, dict]) -> str:
    uv = [item for item in assets.values() if item["topic"] == "uv_aging_wear_morphology"]
    matrix = [
        item for item in assets.values()
        if item["topic"] == "load_distance_morphology_matrix"
        and item["modality"] == "optical_image"
    ]
    lines = [
        "# 第二批实验资产参数核对清单",
        "",
        "本表用于把项目内结构化字段与实验台账、论文、仪器记录和原始文件再次核对。未签字前不应把待确认参数写成确定事实。",
        "",
        "## 紫外老化后摩擦形貌",
        "",
        "| 资产 ID | 老化时长 | 图像角色 | 当前尺度标签 | 载荷/速度/行程 | 图像与样品映射 | 专家结论 |",
        "| --- | ---: | --- | --- | --- | --- | --- |",
    ]
    for item in uv:
        c = item["condition"]
        lines.append(
            f"| `{item['asset_id']}` | {c['aging_duration_h']} h | {c['image_role']} | "
            f"{c['nominal_scale_label_from_filename']} | 待确认 | 待确认 |  |"
        )
    lines.extend(
        [
            "",
            "### 紫外专题统一参数",
            "",
            "| 参数 | 当前记录 | 原始依据位置 | 复核结论 |",
            "| --- | --- | --- | --- |",
            "| 紫外光源 | UVA-340 |  |  |",
            "| 波长范围 | 295-365 nm |  |  |",
            "| 辐照度 | 0.6 W/m² |  |  |",
            "| 摩擦载荷 | 待确认 |  |  |",
            "| 滑动速度/频率 | 待确认 |  |  |",
            "| 行程/循环次数 | 待确认 |  |  |",
            "| 文件名1、2、5.6含义 | 仅作标签 |  |  |",
            "",
            "## 载荷-距离-形貌矩阵",
            "",
            "| 资产 ID | 样品 | 载荷 | 压力 | 距离 | 磨损量 | 硬度 | 映射正确 | 专家备注 |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for item in matrix:
        c = item["condition"]
        lines.append(
            f"| `{item['asset_id']}` | {item['sample_id']} | {c['normal_load_N']} N | "
            f"{c['contact_pressure_MPa']} MPa | {c['sliding_distance_m']} m | "
            f"{c['reported_wear_loss_g']:.4f} g | {c['reported_hardness_HA']:.4f} HA |  |  |"
        )
    lines.extend(
        [
            "",
            "## 温升证据核对",
            "",
            "| 载荷组 | 原始文件 | 与样品/距离映射 | 是否允许进入矩阵 | 专家备注 |",
            "| --- | --- | --- | --- | --- |",
            "| 40 N | `501.csv` 等，待核对 | 待确认 | 否，确认前仅作部分证据 |  |",
            "| 50 N | IRS 原始文件，待解析 | 待确认 | 否 |  |",
            "| 60 N | `601.csv`、`602.csv` 等，待核对 | 待确认 | 否，确认前仅作部分证据 |  |",
            "",
            "复核人：__________  职称/专业：__________  日期：__________  签字：__________",
            "",
        ]
    )
    return "\n".join(lines)


def _profile_id(learner_profile: str) -> str:
    profiles = load_profiles()
    for profile in profiles:
        if learner_profile in {profile["name"], profile["learner_type"]}:
            return profile["profile_id"]
    return "undergrad_basic"


def _score_from_case(case: dict[str, Any]) -> int:
    match = re.search(r"(\d+)%", case["input"])
    return int(match.group(1)) if match else 60


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run batch-2 experimental evidence evaluation.")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    result = run_batch2_evaluation()
    payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    case_map = {item["id"]: item for item in payload["cases"]}
    asset_map = {item["asset_id"]: item for item in catalog["assets"]}
    RESULTS_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SUMMARY_PATH.write_text(render_summary(result), encoding="utf-8")
    EXPERT_TASKS_PATH.write_text(render_expert_tasks(result, case_map), encoding="utf-8")
    ASSET_CHECKLIST_PATH.write_text(render_asset_checklist(asset_map), encoding="utf-8")
    compact = {
        "status": result["automated_status"],
        "manual_review": result["manual_review_status"],
        **result["metrics"],
        "results": str(RESULTS_PATH.relative_to(PROJECT_ROOT)),
        "expert_tasks": str(EXPERT_TASKS_PATH.relative_to(PROJECT_ROOT)),
        "asset_checklist": str(ASSET_CHECKLIST_PATH.relative_to(PROJECT_ROOT)),
    }
    print(json.dumps(compact if args.quiet else result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
