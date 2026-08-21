import re

from app.agents.base_agent import BaseAgent
from app.evidence.catalog import parse_condition_query
from app.models.schemas import AgentStep


class ReviewAgent(BaseAgent):
    agent_name = "专家审核纠偏 Agent"
    role = "检查生成资源的专业概念、知识依据、难度匹配、泛化风险和实操约束。"

    def run(self, context: dict) -> AgentStep:
        resources = context["resources"]
        chunks = context["retrieved_chunks"]
        diagnosis = context["diagnosis_result"]
        evidence_ids = [chunk["id"] for chunk in chunks]
        experimental_evidence = context.get("experimental_evidence", [])
        asset_evidence_ids = [asset.get("asset_id", "") for asset in experimental_evidence]
        review_text = " ".join(
            item
            for item in (
                context.get("learning_goal", ""),
                context.get("feedback_explanation", ""),
                context.get("self_feedback", ""),
            )
            if item
        )
        condition_query = parse_condition_query(review_text)

        risk_points = [
            "形貌观察不能直接等同于机理结论，需要结合工况和多源表征。",
            "训练建议不能替代真实维修放行或适航决策。",
        ]
        if resources["difficulty_match"]["resource_difficulty"] == "降维入门":
            risk_points.append("降维讲义需保留关键边界条件，避免过度简化热-力-氧耦合关系。")
        if not any(chunk.get("source_type") == "practice_task" for chunk in chunks):
            risk_points.append("当前依据中实操任务片段不足，建议追加检查流程约束。")

        corrections = [
            f"围绕“{point}”补充证据来源、实验边界或检查记录模板。"
            for point in diagnosis.weak_points
        ]
        resource_ids = _resource_evidence_ids(resources)
        unsupported_ids = sorted(resource_ids - set(evidence_ids))
        constraints = resources.get("practical_guide", {}).get("constraints", [])
        record_template = resources.get("practical_guide", {}).get("record_template", [])
        graded_quiz = resources.get("graded_quiz", [])
        strategy_id = resources.get("personalization", {}).get("strategy_id", "")
        rejection_reasons = []
        if not evidence_ids:
            rejection_reasons.append("未检索到可绑定的领域知识证据")
        if unsupported_ids:
            rejection_reasons.append(f"生成内容引用了未检索证据：{', '.join(unsupported_ids)}")
        if evidence_ids and not resource_ids:
            rejection_reasons.append("生成资源缺少 evidence_ids 绑定，无法完成知识溯源")
        if not constraints:
            rejection_reasons.append("实操指南缺少边界条件与安全约束")
        if graded_quiz and any(not item.get("explanation") for item in graded_quiz):
            rejection_reasons.append("分阶测试题缺少答案解析")
        record_text = " ".join(str(item) for item in record_template)
        if (
            strategy_id == "graduate"
            and any(keyword in review_text for keyword in ("实验变量", "变量组合", "耦合损伤"))
            and not all(keyword in record_text for keyword in ("自变量", "控制变量"))
        ):
            rejection_reasons.append("科研分析任务缺少自变量、控制变量与对照记录")
        if "图像尺度" in review_text and "尺度" not in record_text:
            rejection_reasons.append("图像判读记录缺少尺度参照字段")
        if (
            diagnosis.score < 60
            and resources.get("difficulty_match", {}).get("resource_difficulty") != "降维入门"
        ):
            rejection_reasons.append("资源难度与基础薄弱学习者不匹配")

        unsupported_claims = _detect_unsupported_claim_requests(review_text)
        evidence_gaps = _evidence_gaps(
            chunks=chunks,
            assets=experimental_evidence,
            condition_query=condition_query,
            unsupported_claims=unsupported_claims,
        )
        for claim in unsupported_claims:
            corrections.append(f"将“{claim}”改写为证据边界内的观察、假设或待验证问题。")
        evidence_sufficiency = _evidence_sufficiency(
            evidence_ids=evidence_ids,
            unsupported_claims=unsupported_claims,
            evidence_gaps=evidence_gaps,
        )
        degraded_output = bool(unsupported_claims) or evidence_sufficiency == "limited"
        requires_regeneration = bool(rejection_reasons) and not context.get("review_retry")
        if requires_regeneration:
            status = "需纠偏后复核"
        elif degraded_output:
            status = "通过，已按证据边界降级"
        else:
            status = "通过，建议带纠偏提示使用"

        verified_claims = _verified_claims(
            evidence_ids=evidence_ids,
            unsupported_ids=unsupported_ids,
            assets=experimental_evidence,
        )
        claim_assessments = _claim_assessments(
            evidence_ids=evidence_ids,
            assets=experimental_evidence,
            unsupported_claims=unsupported_claims,
        )
        review = {
            "status": status,
            "approved": not requires_regeneration,
            "requires_regeneration": requires_regeneration,
            "rejection_reasons": rejection_reasons,
            "risk_points": risk_points,
            "corrections": corrections,
            "evidence_ids": evidence_ids,
            "asset_evidence_ids": asset_evidence_ids,
            "review_scope": {
                "automated_checks": ["引用闭合", "工况字段", "难度匹配", "实操约束", "高风险表述"],
                "expert_review_required": ["专业机理正确性", "实验结论有效性", "真实维修处置"],
            },
            "evidence_sufficiency": evidence_sufficiency,
            "verified_claims": verified_claims,
            "unsupported_claims": unsupported_claims,
            "evidence_gaps": evidence_gaps,
            "claim_assessments": claim_assessments,
            "degraded_output": degraded_output,
            "degradation_notice": (
                "证据不足或请求超出证据边界，系统仅输出训练性观察、假设与补充验证建议。"
                if degraded_output
                else "当前证据可支持训练性讲解；专业结论仍需领域专家复核。"
            ),
            "consistency_check": (
                "存在证据或难度约束问题，需要按纠偏建议重新生成。"
                if requires_regeneration
                else (
                    "引用结构检查通过，但部分请求超出当前证据边界，已降级为待验证表达。"
                    if degraded_output
                    else "自动检查确认引用闭合和边界提示完整；专业机理正确性仍需专家复核。"
                )
            ),
        }
        context["review"] = review

        return self.step(
            input_summary="生成资源 + 检索证据片段",
            output_summary=(
                f"审核要求纠偏，发现 {len(rejection_reasons)} 项阻断问题。"
                if requires_regeneration
                else (
                    f"审核通过并降级 {len(unsupported_claims)} 项越界请求，保留证据限制说明。"
                    if degraded_output
                    else f"审核通过，标记 {len(risk_points)} 个风险点、{len(corrections)} 条纠偏建议。"
                )
            ),
            confidence=0.9,
            evidence_ids=evidence_ids,
            details=review,
        )


def _resource_evidence_ids(resources: dict) -> set[str]:
    evidence_ids = {
        evidence_id
        for section in resources.get("personalized_lecture", {}).get("sections", [])
        for evidence_id in section.get("evidence_ids", [])
    }
    evidence_ids.update(resources.get("practical_guide", {}).get("evidence_ids", []))
    evidence_ids.update(resources.get("case_task", {}).get("evidence_ids", []))
    return evidence_ids


def _detect_unsupported_claim_requests(text: str) -> list[str]:
    compact = text.replace(" ", "")
    findings: list[str] = []
    patterns = (
        (r"(?:单张|仅凭).*(?:完整机理|整个|全部|确定)", "由单一图像确定完整机理或整体分布"),
        (r"(?:单一|单张|仅凭).*(?:形貌|图像).*(?:断定|确定|证明).*(?:失效机理|损伤机理|完整机理)", "由单一形貌或图像断定失效机理"),
        (r"(?:仅凭|只凭|根据)?外观.*(?:内部无损伤|无内部损伤)", "由外观征象排除内部隐蔽损伤"),
        (r"(?:补齐|插补|编造|估算).*(?:温升|数值|参数)", "补齐未记录的实验参数或温升数值"),
        (r"亮度.*(?:直接|等同|当作).*老化程度", "将图像亮度直接等同于老化程度"),
        (r"文件名.*(?:确认|确定|解释).*(?:放大倍数|显微镜参数)", "由文件名推断未确认的显微参数"),
        (r"(?:直接|自动).*(?:适航放行|维修放行)", "以训练输出替代适航或维修放行"),
        (r"(?:替代|代替).*(?:适航放行|维修放行)", "以训练输出替代适航或维修放行"),
        (r"(?:证明|必然|确定).*完整机理", "将机理假设表述为确定性结论"),
    )
    for pattern, message in patterns:
        if re.search(pattern, compact) and message not in findings:
            findings.append(message)
    return findings


def _evidence_gaps(
    chunks: list[dict],
    assets: list[dict],
    condition_query: dict,
    unsupported_claims: list[str],
) -> list[str]:
    gaps: list[str] = []
    if not chunks:
        gaps.append("缺少领域知识片段")
    if condition_query.get("target_topic") and not assets:
        gaps.append("未找到与请求工况绑定的实验资产")
    if assets and not all(asset.get("condition") for asset in assets):
        gaps.append("部分实验资产缺少结构化工况字段")
    modalities = {asset.get("modality") for asset in assets if asset.get("modality")}
    if unsupported_claims and len(modalities) < 2:
        gaps.append("当前多模态证据不足，不能支持确定性机理或整体分布结论")
    if not any(chunk.get("source_type") == "practice_task" for chunk in chunks):
        gaps.append("检索结果缺少专门的实操任务片段")
    return gaps


def _evidence_sufficiency(
    evidence_ids: list[str], unsupported_claims: list[str], evidence_gaps: list[str]
) -> str:
    if not evidence_ids:
        return "insufficient"
    material_gaps = [gap for gap in evidence_gaps if "实操任务片段" not in gap]
    if unsupported_claims or material_gaps:
        return "limited"
    return "sufficient_for_training"


def _verified_claims(
    evidence_ids: list[str], unsupported_ids: list[str], assets: list[dict]
) -> list[str]:
    claims: list[str] = []
    if evidence_ids and not unsupported_ids:
        claims.append("资源中的证据 ID 均来自本次检索结果")
    if assets and all(
        asset.get("source_reference") and asset.get("limitations") for asset in assets
    ):
        claims.append("实验资产具备来源记录和限制说明")
    if assets and all(asset.get("condition") for asset in assets):
        claims.append("实验资产工况字段可追溯")
    return claims


def _claim_assessments(
    evidence_ids: list[str], assets: list[dict], unsupported_claims: list[str]
) -> list[dict]:
    return [
        {
            "category": "实验观察",
            "status": "evidence-bound" if assets else "knowledge-only",
            "basis_ids": [asset.get("asset_id", "") for asset in assets],
            "boundary": "仅描述资产记录中的可见现象，不由单一视野推断整体分布。",
        },
        {
            "category": "工况参数事实",
            "status": "verified-fields" if assets and all(asset.get("condition") for asset in assets) else "limited",
            "basis_ids": [asset.get("asset_id", "") for asset in assets],
            "boundary": "缺失参数保持未知，不进行插补。",
        },
        {
            "category": "损伤机理推断",
            "status": "degraded-hypothesis" if unsupported_claims else "bounded-inference",
            "basis_ids": evidence_ids,
            "boundary": "机理属于受证据约束的解释，仍需交叉表征和专家复核。",
        },
        {
            "category": "维护决策建议",
            "status": "training-only",
            "basis_ids": evidence_ids,
            "boundary": "不能替代适用维修手册、工卡、适航要求和授权放行。",
        },
    ]
