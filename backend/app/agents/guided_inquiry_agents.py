import re

from app.agents.base_agent import BaseAgent
from app.llm.client import maybe_review_guided_answer_with_llm
from app.models.schemas import AgentStep
from app.services.inquiry_service import (
    generate_guided_answer,
    regenerate_guided_answer_with_template,
    synchronize_answer_evidence,
)


class GuidedTutorAgent(BaseAgent):
    agent_name = "启发式讲解 Agent"
    role = "综合学习者画像、诊断薄弱点和 RAG 证据，动态回答学习者追问。"

    def run(self, context: dict) -> AgentStep:
        answer = generate_guided_answer(context)
        context["inquiry_answer"] = answer
        return self.step(
            input_summary=f"学习者追问：{context['inquiry_question']}",
            output_summary=(
                f"已按“{answer['explanation_level']}”生成回答，"
                f"绑定 {len(answer['evidence_ids'])} 条证据；模式={answer['generation_mode']}。"
            ),
            confidence=0.86 if answer["generation_mode"] == "llm" else 0.8,
            evidence_ids=answer["evidence_ids"],
            details={
                "generation_mode": answer["generation_mode"],
                "generation_audit": answer.get("generation_audit", {}),
                "explanation_level": answer["explanation_level"],
                "evidence_titles": answer["evidence_titles"],
                "llm_error": answer.get("llm_error", ""),
            },
        )


class InquiryReviewAgent(BaseAgent):
    agent_name = "追问审核纠偏 Agent"
    role = "核验动态回答的证据闭合、专业边界和过度确定性表述，并可调用 LLM 辅助语义审核。"

    def run(self, context: dict) -> AgentStep:
        answer = context["inquiry_answer"]
        chunks = context.get("retrieved_chunks", [])
        allowed_ids = {chunk.get("id") for chunk in chunks}
        cited_ids = set(answer.get("evidence_ids", []))
        invalid_ids = sorted(cited_ids - allowed_ids)
        text_citations = set(re.findall(r"\[([A-Za-z0-9_.:-]+)\]", answer.get("answer", "")))
        invalid_text_citations = sorted(text_citations - allowed_ids)
        risk_points = []
        if invalid_ids:
            risk_points.append(f"引用了未检索证据：{', '.join(invalid_ids)}")
        if invalid_text_citations:
            risk_points.append(f"回答正文出现未检索证据引用：{', '.join(invalid_text_citations)}")
        if not cited_ids:
            risk_points.append("回答未绑定可追溯证据")
        if len(answer.get("boundaries", [])) < 2:
            risk_points.append("适用边界说明不足")
        if re.search(r"(?:一定|必然|完全证明|直接断定).*(?:机理|原因|失效)", answer.get("answer", "")):
            risk_points.append("存在过度确定性的机理表述")
        input_risk_flags = _input_risk_flags(context["inquiry_question"])
        if input_risk_flags:
            risk_points.append("学习者问题包含越权或诱导编造提示，系统已忽略该部分")

        llm_review, review_mode, review_audit = maybe_review_guided_answer_with_llm(
            context["inquiry_question"], answer, chunks
        )
        corrections = []
        llm_rejected = False
        revision_applied = False
        if llm_review and "review_error" not in llm_review:
            risk_points.extend(str(item) for item in llm_review.get("risk_points", []))
            corrections.extend(str(item) for item in llm_review.get("corrections", []))
            llm_rejected = llm_review.get("approved") is False
            if llm_rejected:
                risk_points.append("LLM 辅助审核未通过候选回答")
            revised = str(llm_review.get("revised_answer", "")).strip()
            revised_citations = set(re.findall(r"\[([A-Za-z0-9_.:-]+)\]", revised))
            if llm_rejected:
                regenerated = regenerate_guided_answer_with_template(
                    context,
                    reason="；".join(str(item) for item in llm_review.get("risk_points", [])),
                )
                answer.clear()
                answer.update(regenerated)
                revision_applied = True
                corrections.append("LLM 候选回答已驳回；为避免修订稿引入二次幻觉，已使用检索证据模板降级重生")
            elif revised and not (revised_citations - allowed_ids):
                # An approved answer does not need semantic rewriting. Preserve the
                # original draft and treat revised_answer as advisory only.
                corrections.append("审核已通过，未采用非必要修订稿")
            elif revised:
                corrections.append("审核修订稿包含未检索证据引用，已拒绝采用")

        risk_points = list(dict.fromkeys(item for item in risk_points if item))
        corrections = list(dict.fromkeys(item for item in corrections if item))
        auto_corrected = bool(invalid_ids or invalid_text_citations or revision_applied)
        if invalid_ids:
            answer["evidence_ids"] = [item for item in answer["evidence_ids"] if item in allowed_ids]
        if invalid_text_citations:
            answer["answer"] = _remove_invalid_citations(
                answer["answer"], set(invalid_text_citations)
            )
            corrections.append("已移除回答正文中未通过本轮检索验证的证据引用")
        synchronize_answer_evidence(answer, chunks, context["inquiry_question"])
        valid_citations = set(answer.get("evidence_ids", []))
        status = "需纠偏" if not valid_citations else (
            "通过，已降级重生" if llm_rejected and revision_applied else (
                "通过，附限制说明" if risk_points else "通过"
            )
        )
        approved = status != "需纠偏"
        review = {
            "status": status,
            "approved": approved,
            "review_mode": review_mode,
            "review_audit": review_audit,
            "risk_points": risk_points,
            "corrections": corrections,
            "evidence_ids": answer.get("evidence_ids", []),
            "input_risk_flags": input_risk_flags,
            "invalid_text_citations": invalid_text_citations,
            "auto_corrected": auto_corrected,
            "candidate_rejected": llm_rejected,
            "revision_applied": revision_applied,
            "boundary_check": "已检查" if len(answer.get("boundaries", [])) >= 2 else "不足",
            "degradation_notice": (
                "当前回答仅用于训练性解释，证据不足部分已保留限制说明。"
                if risk_points else "引用闭合和边界检查通过，专业结论仍需领域专家复核。"
            ),
        }
        if llm_review and llm_review.get("review_error"):
            review["review_error"] = llm_review["review_error"]
        context["inquiry_review"] = review
        return self.step(
            input_summary="动态回答 + 本轮检索证据",
            output_summary=f"审核状态：{status}；发现 {len(risk_points)} 项风险提示。",
            confidence=0.91,
            evidence_ids=answer.get("evidence_ids", []),
            details=review,
        )


def _input_risk_flags(question: str) -> list[str]:
    patterns = (
        (r"忽略.*(?:规则|证据|限制|系统指令)", "attempt_to_override_rules"),
        (r"(?:无需|不要|不需要).*(?:证据|引用|来源)", "request_without_evidence"),
        (r"(?:编造|虚构|补齐).*(?:数据|参数|论文|来源)", "request_to_fabricate"),
        (r"(?:直接|自动).*(?:适航放行|维修放行)", "unsafe_release_request"),
        (r"(?:安全起降.*多少次|起降多少次|剩余寿命|寿命预测)", "unsupported_life_prediction"),
    )
    return [flag for pattern, flag in patterns if re.search(pattern, question)]


def _remove_invalid_citations(text: str, invalid_ids: set[str]) -> str:
    for evidence_id in invalid_ids:
        text = text.replace(f"[{evidence_id}]", "[未通过证据校验]")
    return text


class InquiryDecisionAgent(BaseAgent):
    agent_name = "追问路径决策 Agent"
    role = "根据追问、诊断水平和审核结果决定后续训练动作。"

    def run(self, context: dict) -> AgentStep:
        answer = context["inquiry_answer"]
        review = context["inquiry_review"]
        action = answer["next_action"]
        if not review["approved"] or review.get("candidate_rejected"):
            action = "继续巩固"
        elif review.get("input_risk_flags"):
            action = "继续巩固"
        decision = {
            "next_action": action,
            "follow_up_question": answer["follow_up_question"],
            "practice_task": answer["practice_task"],
            "reason": (
                f"当前诊断得分 {context['diagnosis_result'].score}，"
                f"审核状态为“{review['status']}”，因此推荐“{action}”。"
            ),
        }
        context["inquiry_decision"] = decision
        answer["next_action"] = action
        return self.step(
            input_summary=f"诊断得分={context['diagnosis_result'].score}；审核={review['status']}",
            output_summary=f"推荐动作：{action}；已生成追问和实操任务。",
            confidence=0.89,
            evidence_ids=answer.get("evidence_ids", []),
            details=decision,
        )
