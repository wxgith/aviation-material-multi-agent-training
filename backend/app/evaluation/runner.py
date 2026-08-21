from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from app.agents.orchestrator import orchestrator
from app.core.config import settings
from app.db.database import reset_engine_cache
from app.models.schemas import AgentRunRequest, AnswerSubmission
from app.search.retriever import retrieve_with_rag_metadata
from app.services.data_loader import get_profile, get_questions_by_domain
from app.services.diagnosis_service import evaluate_diagnosis
from app.services.report_service import _feedback_action


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EVALUATION_DIR = PROJECT_ROOT / "evaluation"
CASES_PATH = EVALUATION_DIR / "eval_cases.json"
MULTIDIMENSIONAL_CASES_PATH = EVALUATION_DIR / "eval_cases_multidimensional.json"
SOURCE_REGISTRY_PATH = PROJECT_ROOT / "knowledge_corpus" / "source_registry.json"
DEFAULT_OUTPUT_PATH = EVALUATION_DIR / "automated_results.json"
DEFAULT_MARKDOWN_OUTPUT_PATH = EVALUATION_DIR / "automated_summary.md"
DEFAULT_EXPERT_TASKS_PATH = EVALUATION_DIR / "expert_review_tasks.md"

REQUIRED_FIELDS = {
    "id",
    "test_type",
    "learner_profile",
    "domain",
    "input",
    "expected_key_points",
    "expected_agent_steps",
    "expected_next_action",
    "pass_criteria",
}
EXPECTED_TYPES = {
    "学情诊断测试",
    "知识检索测试",
    "个性化资源生成测试",
    "审核纠偏测试",
    "反馈迭代测试",
}
ProgressCallback = Callable[[dict], None]


def run_evaluation(progress_callback: ProgressCallback | None = None) -> dict:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    _emit_progress(progress_callback, "evaluation", "started", 0, 1, "baseline", "开始离线确定性评测")
    dataset = _evaluate_dataset(cases, progress_callback)
    multidimensional_cases = json.loads(
        MULTIDIMENSIONAL_CASES_PATH.read_text(encoding="utf-8")
    )
    multidimensional = _evaluate_multidimensional_dataset(multidimensional_cases, progress_callback)
    expert_sample = _build_expert_sample(cases)

    original_database_enabled = settings.database_enabled
    original_data_backend = settings.data_backend
    original_es_enabled = settings.es_enabled
    original_retrieval_mode = settings.retrieval_mode
    original_bge_enabled = settings.bge_enabled
    original_embedding_backend = settings.embedding_backend
    original_llm_enabled = settings.llm_enabled

    try:
        # The baseline must be reproducible without Docker and must not write SQL.
        settings.database_enabled = False
        settings.data_backend = "json"
        settings.es_enabled = False
        settings.retrieval_mode = "hybrid"
        settings.bge_enabled = False
        settings.embedding_backend = "none"
        settings.llm_enabled = False
        reset_engine_cache()

        retrieval = _evaluate_retrieval(cases, progress_callback)
        pipeline = _evaluate_pipeline(progress_callback)
        feedback = _evaluate_feedback(cases, progress_callback)
    finally:
        settings.database_enabled = original_database_enabled
        settings.data_backend = original_data_backend
        settings.es_enabled = original_es_enabled
        settings.retrieval_mode = original_retrieval_mode
        settings.bge_enabled = original_bge_enabled
        settings.embedding_backend = original_embedding_backend
        settings.llm_enabled = original_llm_enabled
        reset_engine_cache()

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline_mode": {
            "data_backend": "json",
            "database_enabled": False,
            "es_enabled": False,
            "retrieval_mode": "hybrid",
            "bge_enabled": False,
            "llm_enabled": False,
            "purpose": "deterministic offline regression baseline",
        },
        "dataset": dataset,
        "multidimensional": multidimensional,
        "expert_sample": expert_sample,
        "retrieval": retrieval,
        "pipeline": pipeline,
        "feedback": feedback,
        "manual_review_required": [
            "核心知识点覆盖率需要专家逐项判断生成内容语义是否覆盖。",
            "幻觉率需要专家核对专业断言与 evidence_ids 的一致性。",
            "两条不含明确正确率的反馈用例需要结合自评文本人工复核。",
        ],
        "overall_automated_status": (
            "passed"
            if dataset["passed"]
            and multidimensional["passed"]
            and multidimensional["source_reference_coverage"] == 1.0
            and retrieval["hit_rate"] >= 0.8
            and pipeline["agent_completeness_rate"] == 1.0
            and feedback["decision_accuracy"] >= 0.9
            else "needs_review"
        ),
    }
    _emit_progress(
        progress_callback,
        "evaluation",
        "completed",
        1,
        1,
        "baseline",
        f"离线确定性评测完成：{result['overall_automated_status']}",
    )
    return result


def _evaluate_multidimensional_dataset(cases: list[dict], progress_callback=None) -> dict:
    required_fields = REQUIRED_FIELDS | {"expected_evidence_sources"}
    missing_fields = {
        case.get("id", f"row-{index}"): sorted(required_fields - set(case))
        for index, case in enumerate(cases)
        if required_fields - set(case)
    }
    duplicate_ids = sorted(
        case_id for case_id, count in Counter(case.get("id") for case in cases).items() if count > 1
    )
    registry = json.loads(SOURCE_REGISTRY_PATH.read_text(encoding="utf-8"))
    available_sources = {item["source_id"] for item in registry.get("sources", [])}
    available_sources.update({"local_json_tire", "local_json_brake", "local_json_composite"})
    source_checks = []
    total_references = 0
    matched_references = 0
    total = len(cases)
    for index, case in enumerate(cases, start=1):
        started = time.monotonic()
        _emit_progress(
            progress_callback,
            "multidimensional-validation",
            "started",
            index,
            total,
            case.get("id", f"row-{index}"),
            "校验多维测试来源引用",
        )
        expected = case.get("expected_evidence_sources", [])
        matched = sorted(set(expected) & available_sources)
        missing = sorted(set(expected) - available_sources)
        total_references += len(expected)
        matched_references += len(matched)
        source_checks.append(
            {
                "id": case.get("id"),
                "expected_sources": expected,
                "matched_sources": matched,
                "missing_sources": missing,
                "passed": bool(expected) and not missing,
            }
        )
        _emit_progress(
            progress_callback,
            "multidimensional-validation",
            "completed",
            index,
            total,
            case.get("id", f"row-{index}"),
            "来源引用校验完成",
            started,
        )
    coverage = round(matched_references / total_references, 4) if total_references else 0.0
    passed = len(cases) == 10 and not missing_fields and not duplicate_ids and coverage == 1.0
    return {
        "passed": passed,
        "total_cases": len(cases),
        "type_counts": dict(sorted(Counter(case.get("test_type") for case in cases).items())),
        "domain_counts": dict(sorted(Counter(case.get("domain") for case in cases).items())),
        "missing_fields": missing_fields,
        "duplicate_ids": duplicate_ids,
        "source_references": total_references,
        "matched_source_references": matched_references,
        "source_reference_coverage": coverage,
        "cases": source_checks,
    }


def _build_expert_sample(cases: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = {}
    for case in cases:
        grouped.setdefault(case["test_type"], []).append(case)
    selected = []
    for test_type, group in sorted(grouped.items()):
        for case in (group[0], group[len(group) // 2], group[-1]):
            selected.append(
                {
                    "id": case["id"],
                    "test_type": test_type,
                    "domain": case["domain"],
                    "learner_profile": case["learner_profile"],
                    "review_focus": _review_focus(test_type),
                }
            )
    return {
        "method": "five test types, three deterministic cases per type",
        "total": len(selected),
        "cases": selected,
    }


def _review_focus(test_type: str) -> str:
    if "检索" in test_type:
        return "证据相关性、来源权威性和 evidence_ids 一致性"
    if "生成" in test_type:
        return "核心知识点覆盖、难度适配和实操可执行性"
    if "审核" in test_type:
        return "专业错误、过度外推、风险边界和纠偏有效性"
    if "反馈" in test_type:
        return "next_action 与正确率及学习者反馈是否一致"
    return "薄弱点定位、学习者画像匹配和诊断解释合理性"


def _evaluate_dataset(cases: list[dict], progress_callback=None) -> dict:
    type_counts = Counter(case.get("test_type") for case in cases)
    missing_fields = {}
    total = len(cases)
    for index, case in enumerate(cases, start=1):
        case_id = case.get("id", f"row-{index}")
        started = time.monotonic()
        _emit_progress(
            progress_callback,
            "core-case-validation",
            "started",
            index,
            total,
            case_id,
            "校验字段、分类和期望步骤；本阶段不执行 Agent",
        )
        missing = sorted(REQUIRED_FIELDS - set(case))
        if missing:
            missing_fields[case_id] = missing
        _emit_progress(
            progress_callback,
            "core-case-validation",
            "completed",
            index,
            total,
            case_id,
            "结构校验完成" if not missing else f"缺少字段：{', '.join(missing)}",
            started,
        )
    duplicate_ids = sorted(
        case_id for case_id, count in Counter(case.get("id") for case in cases).items() if count > 1
    )
    passed = (
        len(cases) == 50
        and set(type_counts) == EXPECTED_TYPES
        and all(type_counts[item] == 10 for item in EXPECTED_TYPES)
        and not missing_fields
        and not duplicate_ids
    )
    return {
        "passed": passed,
        "total_cases": len(cases),
        "type_counts": dict(sorted(type_counts.items())),
        "missing_fields": missing_fields,
        "duplicate_ids": duplicate_ids,
    }


def _evaluate_retrieval(cases: list[dict], progress_callback=None) -> dict:
    results = []
    retrieval_cases = [case for case in cases if case["test_type"] == "知识检索测试"]
    total = len(retrieval_cases)
    for index, case in enumerate(retrieval_cases, start=1):
        started = time.monotonic()
        _emit_progress(
            progress_callback,
            "retrieval",
            "started",
            index,
            total,
            case["id"],
            case["input"],
        )
        expected_ids = _extract_evidence_ids(case["expected_key_points"])
        result = retrieve_with_rag_metadata(
            domain=case["domain"],
            weak_points=[],
            learning_goal=case["input"],
            learner_type=case["learner_profile"],
            top_k=3,
        )
        evidence_ids = result["evidence_ids"]
        matched_ids = sorted(set(expected_ids) & set(evidence_ids))
        results.append(
            {
                "id": case["id"],
                "expected_evidence_ids": expected_ids,
                "actual_evidence_ids": evidence_ids,
                "matched_evidence_ids": matched_ids,
                "passed": bool(matched_ids),
                "knowledge_source": result["knowledge_source"],
                "effective_retrieval_mode": result["effective_retrieval_mode"],
            }
        )
        _emit_progress(
            progress_callback,
            "retrieval",
            "completed",
            index,
            total,
            case["id"],
            f"命中 {len(matched_ids)} 条期望证据；来源 {result['knowledge_source']}",
            started,
        )

    passed_count = sum(item["passed"] for item in results)
    total = len(results)
    return {
        "passed": passed_count,
        "total": total,
        "hit_rate": round(passed_count / total, 4) if total else 0.0,
        "cases": results,
    }


def _evaluate_pipeline(progress_callback=None) -> dict:
    results = []
    domains = ("tire", "brake", "composite")
    for index, domain in enumerate(domains, start=1):
        started = time.monotonic()
        _emit_progress(
            progress_callback,
            "agent-pipeline",
            "started",
            index,
            len(domains),
            domain,
            "执行 6 Agent 离线样例",
        )
        profile = get_profile("undergrad_basic")
        questions = get_questions_by_domain(domain)
        answers = [
            AnswerSubmission(question_id=question["id"], answer=question["answer"])
            for question in questions
        ]
        diagnosis = evaluate_diagnosis(profile["profile_id"], domain, answers)
        session = orchestrator.run(
            AgentRunRequest(
                profile_id=profile["profile_id"],
                domain=domain,
                diagnosis_result=diagnosis,
                learning_goal=profile["default_goal"],
            )
        )
        step_names = [step.agent_name for step in session["agent_steps"]]
        resources = session["resources"]
        resources_complete = all(
            resources.get(key)
            for key in ("personalized_lecture", "practical_guide", "graded_quiz", "case_task")
        )
        review_complete = bool(session["review"].get("risk_points")) and bool(
            session["review"].get("evidence_ids")
        )
        passed = len(step_names) == 6 and resources_complete and review_complete
        results.append(
            {
                "domain": domain,
                "passed": passed,
                "agent_steps": step_names,
                "resources_complete": resources_complete,
                "review_complete": review_complete,
                "retrieval_source": session["retrieval_source"],
                "retrieval_mode": session["retrieval_mode"],
            }
        )
        _emit_progress(
            progress_callback,
            "agent-pipeline",
            "completed",
            index,
            len(domains),
            domain,
            f"Agent 步骤 {len(step_names)}；来源 {session['retrieval_source']}",
            started,
        )

    passed_count = sum(item["passed"] for item in results)
    total = len(results)
    return {
        "passed": passed_count,
        "total": total,
        "agent_completeness_rate": round(passed_count / total, 4) if total else 0.0,
        "cases": results,
    }


def _evaluate_feedback(cases: list[dict], progress_callback=None) -> dict:
    results = []
    feedback_cases = [case for case in cases if case["test_type"] == "反馈迭代测试"]
    total_cases = len(feedback_cases)
    for index, case in enumerate(feedback_cases, start=1):
        started = time.monotonic()
        _emit_progress(
            progress_callback,
            "feedback-decision",
            "started",
            index,
            total_cases,
            case["id"],
            case["input"],
        )
        score_match = re.search(r"(\d+)%", case["input"])
        if not score_match:
            results.append(
                {
                    "id": case["id"],
                    "status": "manual_review",
                    "reason": "输入未提供明确正确率",
                    "expected_next_action": case["expected_next_action"],
                }
            )
            _emit_progress(
                progress_callback,
                "feedback-decision",
                "completed",
                index,
                total_cases,
                case["id"],
                "未提供明确正确率，进入人工复核",
                started,
            )
            continue
        score = int(score_match.group(1))
        actual_action, _ = _feedback_action(score, "")
        results.append(
            {
                "id": case["id"],
                "status": "passed" if actual_action == case["expected_next_action"] else "failed",
                "score": score,
                "expected_next_action": case["expected_next_action"],
                "actual_next_action": actual_action,
            }
        )
        _emit_progress(
            progress_callback,
            "feedback-decision",
            "completed",
            index,
            total_cases,
            case["id"],
            f"{score}% -> {actual_action}",
            started,
        )

    automated = [item for item in results if item["status"] != "manual_review"]
    passed_count = sum(item["status"] == "passed" for item in automated)
    total = len(automated)
    return {
        "passed": passed_count,
        "automated_total": total,
        "manual_review_total": len(results) - total,
        "decision_accuracy": round(passed_count / total, 4) if total else 0.0,
        "cases": results,
    }


def _emit_progress(
    callback,
    stage: str,
    status: str,
    current: int,
    total: int,
    case_id: str,
    message: str,
    started: float | None = None,
) -> None:
    if callback is None:
        return
    callback(
        {
            "stage": stage,
            "status": status,
            "current": current,
            "total": total,
            "case_id": case_id,
            "message": message,
            "elapsed_ms": round((time.monotonic() - started) * 1000) if started else 0,
        }
    )


def _extract_evidence_ids(key_points: list[str]) -> list[str]:
    return sorted(
        {
            evidence_id
            for key_point in key_points
            for evidence_id in re.findall(r"(?:tire|brake|composite)-k\d+", key_point)
        }
    )


def render_markdown_summary(result: dict) -> str:
    dataset = result["dataset"]
    multidimensional = result["multidimensional"]
    retrieval = result["retrieval"]
    pipeline = result["pipeline"]
    feedback = result["feedback"]
    sample_rows = [
        f"| {item['id']} | {item['test_type']} | {item['domain']} | {item['review_focus']} |"
        for item in result["expert_sample"]["cases"]
    ]
    return "\n".join(
        [
            "# 自动测评证据摘要",
            "",
            f"生成时间：`{result['generated_at']}`",
            "",
            "## 自动验收结果",
            "",
            "| 指标 | 结果 | 状态 |",
            "| --- | ---: | --- |",
            f"| 核心测评集结构完整性 | {dataset['total_cases']}/50 | {'通过' if dataset['passed'] else '需检查'} |",
            f"| 多维增强用例完整性 | {multidimensional['total_cases']}/10 | {'通过' if multidimensional['passed'] else '需检查'} |",
            f"| 多维用例来源登记覆盖率 | {multidimensional['source_reference_coverage']:.0%} | {'通过' if multidimensional['source_reference_coverage'] == 1 else '需检查'} |",
            f"| 检索 Top-3 命中率 | {retrieval['hit_rate']:.0%} ({retrieval['passed']}/{retrieval['total']}) | {'通过' if retrieval['hit_rate'] >= .8 else '需检查'} |",
            f"| Agent 完整率 | {pipeline['agent_completeness_rate']:.0%} ({pipeline['passed']}/{pipeline['total']}) | {'通过' if pipeline['agent_completeness_rate'] == 1 else '需检查'} |",
            f"| 规则反馈决策准确率 | {feedback['decision_accuracy']:.0%} ({feedback['passed']}/{feedback['automated_total']}) | {'通过' if feedback['decision_accuracy'] >= .9 else '需检查'} |",
            "",
            f"自动结论：`{result['overall_automated_status']}`。",
            "",
            "## 专家分层抽检清单",
            "",
            "| 用例 ID | 类型 | 领域 | 复核重点 |",
            "| --- | --- | --- | --- |",
            *sample_rows,
            "",
            "## 必须人工完成的指标",
            "",
            "- 核心知识点覆盖率。",
            "- 幻觉率及专业断言与 evidence_ids 的一致性。",
            "- 资源难度适配准确率。",
            "- 两条定性反馈用例和维修边界表述。",
            "",
            "> 自动测评用于工程回归，不替代航空工程材料领域专家结论。",
            "",
        ]
    )


def render_expert_review_tasks(result: dict, cases: list[dict]) -> str:
    case_map = {case["id"]: case for case in cases}
    sections = [
        "# 专家分层抽检任务单",
        "",
        "本任务单由测评 runner 固定抽取，每类核心任务 3 条，共 15 条。请结合实际系统输出和 evidence_ids 评分，不要仅按预期答案判断。",
        "",
        "## 评分规则",
        "",
        "- 专业正确性、证据一致性、难度适配、实操可行性均采用 1 至 5 分。",
        "- 幻觉判定填写“是”或“否”。无知识依据、与证据冲突或越过维修判定边界的断言记为幻觉。",
        "- 建议通过标准：正确性和证据一致性不低于 4 分，难度与实操不低于 3 分，且无幻觉。",
        "",
    ]
    for index, item in enumerate(result["expert_sample"]["cases"], start=1):
        case = case_map[item["id"]]
        key_points = "；".join(case.get("expected_key_points", []))
        sections.extend(
            [
                f"## {index}. {item['id']} | {item['test_type']} | {item['domain']}",
                "",
                f"- 学习者画像：{case['learner_profile']}",
                f"- 测试输入：{case['input']}",
                f"- 预期关键点：{key_points}",
                f"- 预期下一动作：{case.get('expected_next_action', '')}",
                f"- 复核重点：{item['review_focus']}",
                "",
                "| 评分项 | 填写 |",
                "| --- | --- |",
                "| 专业正确性（1-5） |  |",
                "| 证据一致性（1-5） |  |",
                "| 难度适配（1-5） |  |",
                "| 实操可行性（1-5） |  |",
                "| 是否存在幻觉 |  |",
                "| 结论（通过/修改后通过/不通过） |  |",
                "| evidence_ids |  |",
                "| 问题与修改建议 |  |",
                "",
            ]
        )
    sections.extend(
        [
            "## 汇总结论",
            "",
            "| 项目 | 填写 |",
            "| --- | --- |",
            "| 抽检通过数 |  |",
            "| 核心知识点覆盖率 |  |",
            "| 幻觉率 |  |",
            "| 难度适配准确率 |  |",
            "| 主要问题 |  |",
            "| 总体结论 |  |",
            "| 专家姓名及职称 |  |",
            "| 专业方向 |  |",
            "| 复核日期 |  |",
            "| 签字 |  |",
            "",
        ]
    )
    return "\n".join(sections)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deterministic competition evaluation baseline.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path for the JSON result. Use '-' to print only.",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=DEFAULT_MARKDOWN_OUTPUT_PATH,
        help="Path for the human-readable Markdown summary.",
    )
    parser.add_argument(
        "--expert-tasks-output",
        type=Path,
        default=DEFAULT_EXPERT_TASKS_PATH,
        help="Path for the 15-case expert review task sheet.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only the compact evaluation summary.",
    )
    parser.add_argument(
        "--progress",
        action="store_true",
        help="Stream stage and case progress to stdout while the evaluation runs.",
    )
    args = parser.parse_args()

    def print_progress(event: dict) -> None:
        marker = "START" if event["status"] == "started" else "DONE "
        elapsed = f" elapsed={event['elapsed_ms']}ms" if event["elapsed_ms"] else ""
        print(
            f"[{marker}] stage={event['stage']} "
            f"case={event['case_id']} {event['current']}/{event['total']} "
            f"{event['message']}{elapsed}",
            flush=True,
        )

    result = run_evaluation(progress_callback=print_progress if args.progress else None)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if str(args.output) != "-":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    if str(args.markdown_output) != "-":
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(render_markdown_summary(result), encoding="utf-8")
    if str(args.expert_tasks_output) != "-":
        args.expert_tasks_output.parent.mkdir(parents=True, exist_ok=True)
        cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
        args.expert_tasks_output.write_text(
            render_expert_review_tasks(result, cases), encoding="utf-8"
        )
    if args.quiet:
        print(
            json.dumps(
                {
                    "status": result["overall_automated_status"],
                    "core_cases": result["dataset"]["total_cases"],
                    "multidimensional_cases": result["multidimensional"]["total_cases"],
                    "source_reference_coverage": result["multidimensional"][
                        "source_reference_coverage"
                    ],
                    "retrieval_hit_rate": result["retrieval"]["hit_rate"],
                    "agent_completeness_rate": result["pipeline"][
                        "agent_completeness_rate"
                    ],
                    "feedback_decision_accuracy": result["feedback"]["decision_accuracy"],
                    "expert_sample_cases": result["expert_sample"]["total"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(rendered)


if __name__ == "__main__":
    main()
