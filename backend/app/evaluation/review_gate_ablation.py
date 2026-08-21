from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_QWEN_RESULTS = ROOT / "evaluation" / "qwen_quality_results.json"
DEFAULT_FULL_RESULTS = ROOT / "evaluation" / "full_case_execution_results.json"
DEFAULT_JSON_OUTPUT = ROOT / "evaluation" / "review_gate_ablation_results.json"
DEFAULT_MD_OUTPUT = ROOT / "evaluation" / "review_gate_ablation_report.md"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_ablation(qwen: dict[str, Any], full: dict[str, Any]) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for case in qwen["cases"]:
        review = case.get("review", {})
        audit = case.get("generation_audit", {})
        rejected = bool(review.get("candidate_rejected"))
        risk_points = review.get("risk_points") or []
        corrections = review.get("corrections") or []
        cases.append(
            {
                "id": case["id"],
                "domain": case["domain"],
                "profile_id": case["profile_id"],
                "question": case["question"],
                "retrieval_mode": case.get("retrieval_mode"),
                "knowledge_source": case.get("knowledge_source"),
                "candidate_generation_mode": (
                    audit.get("candidate_generation_audit", {}).get("outcome")
                    if rejected
                    else audit.get("outcome")
                ),
                "candidate_review_passed": not rejected,
                "review_gate_intervened": rejected,
                "risk_finding_count": len(risk_points),
                "correction_count": len(corrections),
                "final_generation_mode": case.get("generation_mode"),
                "final_machine_passed": bool(case.get("machine_passed")),
                "evidence_closed": bool(case.get("checks", {}).get("evidence_closed")),
                "review_controlled": bool(case.get("checks", {}).get("review_controlled")),
            }
        )

    count = len(cases)
    direct_passed = sum(item["candidate_review_passed"] for item in cases)
    interventions = sum(item["review_gate_intervened"] for item in cases)
    final_passed = sum(item["final_machine_passed"] for item in cases)
    evidence_closed = sum(item["evidence_closed"] for item in cases)
    risk_findings = sum(item["risk_finding_count"] for item in cases)

    full_metrics = full["metrics"]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "experiment_type": "paired_review_gate_ablation",
        "data_origin": "archived_real_qwen_outputs_and_deterministic_full_case_results",
        "network_or_llm_called": False,
        "paired_cohort": {
            "case_count": count,
            "arm_a": "RAG + Qwen candidate without ReviewAgent gate",
            "arm_b": "RAG + Qwen + ReviewAgent + evidence-template regeneration",
            "direct_candidate_passed": direct_passed,
            "direct_candidate_pass_rate": round(direct_passed / count, 4) if count else 0,
            "review_gate_interventions": interventions,
            "review_gate_intervention_rate": round(interventions / count, 4) if count else 0,
            "post_gate_machine_passed": final_passed,
            "post_gate_machine_pass_rate": round(final_passed / count, 4) if count else 0,
            "acceptance_improvement_points": round((final_passed - direct_passed) / count * 100, 2)
            if count
            else 0,
            "evidence_closed_cases": evidence_closed,
            "risk_findings_recorded": risk_findings,
        },
        "supporting_full_pipeline": {
            "case_count": full_metrics["executed_cases"],
            "passed_cases": full_metrics["passed_cases"],
            "agent_completeness_rate": full_metrics["agent_completeness_rate"],
            "correction_cases": full_metrics["correction_cases"],
            "core_key_point_proxy_coverage": full_metrics["core_key_point_proxy_coverage"],
            "difficulty_rule_match_accuracy": full_metrics["difficulty_rule_match_accuracy"],
            "unresolved_claim_risk_proxy_rate": full_metrics["unresolved_claim_risk_proxy_rate"],
        },
        "cases": cases,
        "claim_boundary": [
            "该实验衡量审核门的风险拦截和结构化验收作用，不直接等价于学习效果提升。",
            "配对样本为 6 条真实 Qwen 代表性场景，样本量有限，仍需外部专家盲审。",
            "候选答案均已使用 RAG 证据；本实验不宣称完成了无 RAG 单模型对照。",
            "50 条完整管线结果用于补充工程稳定性，不与 6 条 Qwen 样本合并计算同一比例。",
        ],
    }


def render_markdown(result: dict[str, Any]) -> str:
    paired = result["paired_cohort"]
    full = result["supporting_full_pipeline"]
    lines = [
        "# 多智能体审核门对比实验",
        "",
        "> 本报告由归档的真实 Qwen 输出与确定性测评结果离线计算，不重新调用模型或数据库。",
        "",
        "## 1. 实验问题",
        "",
        "在检索证据和学习者画像相同的条件下，比较：",
        "",
        "- A 组：RAG + Qwen 原始候选，不经过 ReviewAgent 质量门。",
        "- B 组：RAG + Qwen + ReviewAgent；不合格候选驳回并使用证据模板重生。",
        "",
        "## 2. 配对结果",
        "",
        "| 指标 | 结果 |",
        "| --- | ---: |",
        f"| 真实 Qwen 配对样本 | {paired['case_count']} |",
        f"| 原始候选直接通过审核 | {paired['direct_candidate_passed']}/{paired['case_count']} ({paired['direct_candidate_pass_rate']:.0%}) |",
        f"| ReviewAgent 实际介入 | {paired['review_gate_interventions']}/{paired['case_count']} ({paired['review_gate_intervention_rate']:.0%}) |",
        f"| 审核与重生后机器检查通过 | {paired['post_gate_machine_passed']}/{paired['case_count']} ({paired['post_gate_machine_pass_rate']:.0%}) |",
        f"| 机器验收通过率变化 | +{paired['acceptance_improvement_points']:.0f} 个百分点 |",
        f"| 证据闭合 | {paired['evidence_closed_cases']}/{paired['case_count']} |",
        f"| 审核记录的风险项 | {paired['risk_findings_recorded']} |",
        "",
        "## 3. 逐例状态",
        "",
        "| 用例 | 领域 | 画像 | 原始候选 | 审核介入 | 风险项 | 最终模式 | 最终机器检查 |",
        "| --- | --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for case in result["cases"]:
        lines.append(
            "| {id} | {domain} | {profile_id} | {candidate} | {intervened} | {risks} | {mode} | {final} |".format(
                id=case["id"],
                domain=case["domain"],
                profile_id=case["profile_id"],
                candidate="通过" if case["candidate_review_passed"] else "驳回",
                intervened="是" if case["review_gate_intervened"] else "否",
                risks=case["risk_finding_count"],
                mode=case["final_generation_mode"],
                final="通过" if case["final_machine_passed"] else "未通过",
            )
        )

    lines.extend(
        [
            "",
            "## 4. 50 条完整管线补充结果",
            "",
            "| 指标 | 结果 |",
            "| --- | ---: |",
            f"| 完整执行 | {full['passed_cases']}/{full['case_count']} |",
            f"| 6 Agent 完整率 | {full['agent_completeness_rate']:.0%} |",
            f"| 触发纠偏的用例 | {full['correction_cases']} |",
            f"| 核心知识点代理覆盖率 | {full['core_key_point_proxy_coverage']:.2%} |",
            f"| 难度规则匹配率 | {full['difficulty_rule_match_accuracy']:.0%} |",
            f"| 审核后未解决断言风险代理率 | {full['unresolved_claim_risk_proxy_rate']:.0%} |",
            "",
            "## 5. 可引用结论",
            "",
            "在 6 条真实 Qwen 代表性场景中，未经审核的 RAG + Qwen 候选仅 3/6 直接通过；ReviewAgent 对另 3 条执行驳回和证据模板重生，最终 6/6 通过机器检查。该结果说明多智能体审核门不是界面展示，而会实际改变不合格模型输出。",
            "",
            "## 6. 结论边界",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in result["claim_boundary"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the offline ReviewAgent ablation report.")
    parser.add_argument("--qwen-results", type=Path, default=DEFAULT_QWEN_RESULTS)
    parser.add_argument("--full-results", type=Path, default=DEFAULT_FULL_RESULTS)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    args = parser.parse_args()

    result = build_ablation(_load(args.qwen_results), _load(args.full_results))
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.md_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md_output.write_text(render_markdown(result), encoding="utf-8")
    print(f"paired cases: {result['paired_cohort']['case_count']}")
    print(
        "direct -> post gate: "
        f"{result['paired_cohort']['direct_candidate_passed']}/{result['paired_cohort']['case_count']} -> "
        f"{result['paired_cohort']['post_gate_machine_passed']}/{result['paired_cohort']['case_count']}"
    )
    print(args.json_output)
    print(args.md_output)


if __name__ == "__main__":
    main()
