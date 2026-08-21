import re
from typing import Any

from app.llm.client import maybe_generate_guided_answer_with_llm


DOMAIN_TASKS = {
    "tire": "选取两条不同工况的胎面证据，按“可见现象—工况—可能机制—待补检测”填写对照记录。",
    "brake": "按温度、摩擦性能、表面形貌和限制条件建立一张制动材料失效判读表。",
    "composite": "对照表面征象与无损检测结果，分别记录可见损伤、隐蔽损伤假设和待验证区域。",
}


def generate_guided_answer(context: dict[str, Any]) -> dict[str, Any]:
    chunks = context.get("retrieved_chunks", [])
    history = context.get("inquiry_history", [])
    llm_answer, generation_mode, generation_audit = maybe_generate_guided_answer_with_llm(
        profile=context["profile"],
        domain=context["domain"],
        diagnosis=context["diagnosis_result"],
        learning_goal=context.get("original_learning_goal", context.get("learning_goal", "")),
        question=context["inquiry_question"],
        retrieved_chunks=chunks,
        history=history,
        page_context=context.get("page_context"),
    )

    if llm_answer and "llm_error" not in llm_answer:
        answer = _normalize_llm_answer(llm_answer, context)
        answer["generation_mode"] = generation_mode
        answer["generation_audit"] = generation_audit
        return answer

    answer = _template_answer(context)
    _apply_high_risk_decision_guard(answer, context)
    answer["generation_mode"] = generation_mode
    answer["generation_audit"] = generation_audit
    if llm_answer and llm_answer.get("llm_error"):
        answer["llm_error"] = llm_answer["llm_error"]
    return answer


def regenerate_guided_answer_with_template(
    context: dict[str, Any], reason: str = "审核 Agent 驳回候选回答"
) -> dict[str, Any]:
    """Create a deterministic evidence-bound answer after semantic review rejects an LLM draft."""
    candidate_audit = dict(
        context.get("inquiry_answer", {}).get("generation_audit", {})
    )
    answer = _template_answer(context)
    _apply_high_risk_decision_guard(answer, context)
    answer["generation_mode"] = "review-template-fallback"
    answer["generation_audit"] = {
        "prompt_version": "review-template-fallback-v1",
        "model": "deterministic-template",
        "provider_configured": False,
        "latency_ms": 0,
        "outcome": "review_fallback",
        "fallback_reason": reason[:500],
        "candidate_generation_audit": candidate_audit,
    }
    return answer


def _normalize_llm_answer(answer: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    chunks = context.get("retrieved_chunks", [])
    allowed = {chunk.get("id"): chunk for chunk in chunks if chunk.get("id")}
    evidence_ids = [
        evidence_id
        for evidence_id in answer.get("evidence_ids", [])
        if evidence_id in allowed
    ]
    if not evidence_ids:
        evidence_ids = [
            chunk["id"]
            for chunk in _select_diverse_chunks(chunks, limit=3)
            if chunk.get("id")
        ]
    text = str(answer.get("answer", "")).strip()
    if not text:
        raise ValueError("LLM 追问回答缺少 answer。")
    if evidence_ids and not any(f"[{evidence_id}]" in text for evidence_id in evidence_ids):
        text += "\n\n证据索引：" + "、".join(f"[{evidence_id}]" for evidence_id in evidence_ids)

    boundaries = [str(item).strip() for item in answer.get("boundaries", []) if str(item).strip()]
    boundaries.extend(_default_boundaries(context["domain"]))
    normalized = {
        "answer": text,
        # The display label is system-owned so one learner profile always maps to
        # one auditable explanation tier. The model still controls the answer body.
        "explanation_level": _explanation_level(context["profile"]),
        "evidence_ids": list(dict.fromkeys(evidence_ids)),
        "evidence_titles": [allowed[evidence_id].get("title", "") for evidence_id in evidence_ids],
        "evidence_snippets": _evidence_snippets(
            chunks, evidence_ids, context["inquiry_question"]
        ),
        "boundaries": list(dict.fromkeys(boundaries))[:5],
        "follow_up_question": str(answer.get("follow_up_question") or _follow_up_question(context)),
        "practice_task": str(answer.get("practice_task") or DOMAIN_TASKS[context["domain"]]),
        "next_action": _normalize_action(answer.get("next_action"), context),
    }
    _apply_high_risk_decision_guard(normalized, context)
    return normalized


def _apply_high_risk_decision_guard(answer: dict[str, Any], context: dict[str, Any]) -> None:
    question = context["inquiry_question"]
    evidence_ids = answer.get("evidence_ids", [])
    citations = "".join(f"[{evidence_id}]" for evidence_id in evidence_ids[:3])
    if re.search(r"(?:安全起降.*多少次|起降多少次|剩余寿命|寿命预测)", question):
        answer["answer"] = (
            "当前证据不足，不能精确计算剩余安全起降次数或剩余寿命。"
            "本轮检索证据只能说明实验室工况下的观察量，尚未建立实验滑动距离与真实起降循环的等效映射；"
            "同时缺少同一轮胎的服役历史、损伤几何测量、连续检测趋势和适用维修限值。"
            f"因此只能提出补充检测与资料核验要求，不能输出确定次数。{citations}"
        )
        answer["next_action"] = "继续巩固"
    elif re.search(r"(?:适航放行|维修放行|直接放行|允许放行)", question):
        answer["answer"] = (
            "不能依据单张图像或本系统回答给出适航或维修放行结论。"
            "当前证据仅用于训练性损伤观察与检查建议；实际处置必须核对适用维修手册、工卡、"
            f"检测记录和授权流程。{citations}"
        )
        answer["next_action"] = "继续巩固"


def synchronize_answer_evidence(
    answer: dict[str, Any], chunks: list[dict], question: str = ""
) -> None:
    """Keep final answer citations, evidence metadata and snippets consistent."""
    allowed = {chunk.get("id"): chunk for chunk in chunks if chunk.get("id")}
    declared_ids = [
        evidence_id
        for evidence_id in answer.get("evidence_ids", [])
        if evidence_id in allowed
    ]
    answer_text = str(answer.get("answer", ""))
    text_ids = [evidence_id for evidence_id in allowed if evidence_id in answer_text]
    used = set(declared_ids) | {evidence_id for evidence_id in text_ids if evidence_id in allowed}
    evidence_ids = [chunk["id"] for chunk in chunks if chunk.get("id") in used]
    if not evidence_ids:
        evidence_ids = [
            chunk["id"]
            for chunk in _select_diverse_chunks(chunks, limit=3)
            if chunk.get("id")
        ]
    text = answer_text.strip()
    if evidence_ids and not any(f"[{evidence_id}]" in text for evidence_id in evidence_ids):
        text += "\n\n证据索引：" + "、".join(f"[{evidence_id}]" for evidence_id in evidence_ids)
    answer["answer"] = text
    answer["evidence_ids"] = evidence_ids
    answer["evidence_titles"] = [allowed[evidence_id].get("title", "") for evidence_id in evidence_ids]
    answer["evidence_snippets"] = _evidence_snippets(chunks, evidence_ids, question)


def _template_answer(context: dict[str, Any]) -> dict[str, Any]:
    chunks = context.get("retrieved_chunks", [])
    selected = _select_question_relevant_chunks(
        chunks, context["inquiry_question"], limit=3
    )
    evidence_ids = [chunk.get("id", "") for chunk in selected if chunk.get("id")]
    learner_type = context["profile"].get("learner_type", "学习者")
    question = context["inquiry_question"]
    diagnosis = context["diagnosis_result"]
    weak_points = "、".join(diagnosis.weak_points) or "当前问题涉及的知识点"

    if not selected:
        conclusion = "当前知识库没有检索到足以支撑该问题的证据，因此不能给出确定性专业结论。"
        evidence_lines = ["建议补充与问题工况一致的实验记录、表征结果或权威技术资料后再判断。"]
    else:
        conclusion = (
            f"针对“{question}”，当前证据支持先从可观察事实和工况边界建立判断，"
            "不能由单一形貌或单个指标直接跳到确定性损伤机理。"
        )
        evidence_lines = [
            f"{index}. {chunk.get('title', '知识片段')}："
            f"{_clean_excerpt(chunk.get('content', ''), question=question)} "
            f"[{chunk.get('id', '')}]"
            for index, chunk in enumerate(selected, 1)
        ]

    adaptation = _adaptation_sentence(learner_type, weak_points)
    answer_text = "\n".join(
        [
            conclusion,
            "",
            "证据链：",
            *evidence_lines,
            "",
            f"个性化讲解：{adaptation}",
            "回答中的机理解释属于受证据约束的训练性推断；若要形成工程结论，还需结合一致工况下的多源表征和适用规范。",
        ]
    )
    return {
        "answer": answer_text,
        "explanation_level": _explanation_level(context["profile"]),
        "evidence_ids": evidence_ids,
        "evidence_titles": [chunk.get("title", "") for chunk in selected],
        "evidence_snippets": _evidence_snippets(chunks, evidence_ids, question),
        "boundaries": _default_boundaries(context["domain"]),
        "follow_up_question": _follow_up_question(context),
        "practice_task": DOMAIN_TASKS[context["domain"]],
        "next_action": _normalize_action(None, context),
    }


def _evidence_snippets(
    chunks: list[dict], evidence_ids: list[str], question: str = ""
) -> list[dict[str, str]]:
    by_id = {chunk.get("id"): chunk for chunk in chunks}
    return [
        {
            "evidence_id": evidence_id,
            "title": str(by_id[evidence_id].get("title", "")),
            "snippet": _clean_excerpt(
                by_id[evidence_id].get("content", ""), limit=180, question=question
            ),
            "source_id": str(by_id[evidence_id].get("source_id", "")),
        }
        for evidence_id in evidence_ids
        if evidence_id in by_id
    ]


def _clean_excerpt(content: Any, limit: int = 260, question: str = "") -> str:
    text = re.sub(r"\s+", " ", str(content)).strip()
    exact_condition_row = _extract_exact_condition_row(text, question)
    if exact_condition_row:
        return exact_condition_row[:limit] + (
            "…" if len(exact_condition_row) > limit else ""
        )
    condition_values = re.findall(r"\d+(?:\.\d+)?\s*(?:N|m|MPa|°C|h|d)\b", question)
    if len(condition_values) >= 2:
        pattern = ".{0,50}" + ".{0,160}".join(
            re.escape(value).replace(r"\ ", r"\s*") for value in condition_values[:2]
        ) + ".{0,80}"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            text = match.group(0).strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def _extract_exact_condition_row(content: str, question: str) -> str:
    """Extract a complete Markdown-table row for an explicit load/distance query."""
    load_match = re.search(r"(?<!\d)(\d+(?:\.\d+)?)\s*N\b", question, re.IGNORECASE)
    distance_match = re.search(r"(?<!\d)(\d+(?:\.\d+)?)\s*m\b", question, re.IGNORECASE)
    if not (load_match and distance_match):
        return ""

    load = re.escape(load_match.group(1))
    distance = re.escape(distance_match.group(1))
    rows = re.split(r"\|\s*\|", content)
    for row in rows:
        if not re.search(rf"(?<!\d){load}\s*N\b", row, re.IGNORECASE):
            continue
        if not re.search(rf"(?<!\d){distance}\s*m\b", row, re.IGNORECASE):
            continue
        fields = [field.strip(" `") for field in row.strip(" |").split("|")]
        if len(fields) >= 5:
            return "精确工况记录：" + "；".join(field for field in fields if field)
        return "精确工况记录：" + row.strip(" |")
    return ""


def _select_diverse_chunks(chunks: list[dict], limit: int) -> list[dict]:
    selected: list[dict] = []
    seen_sources: set[str] = set()
    for chunk in chunks:
        source_id = str(chunk.get("source_id") or chunk.get("id") or "")
        if source_id in seen_sources:
            continue
        selected.append(chunk)
        seen_sources.add(source_id)
        if len(selected) >= limit:
            return selected
    return selected


def _select_question_relevant_chunks(
    chunks: list[dict], question: str, limit: int
) -> list[dict]:
    keywords = _question_keywords(question)
    ranked = []
    for index, chunk in enumerate(chunks):
        searchable = " ".join(
            [
                str(chunk.get("title", "")),
                " ".join(str(item) for item in chunk.get("tags", [])),
                str(chunk.get("content", "")),
            ]
        ).lower()
        score = sum(5 if keyword in str(chunk.get("title", "")).lower() else 2 for keyword in keywords if keyword in searchable)
        if _extract_exact_condition_row(str(chunk.get("content", "")), question):
            score += 50
        score += max(0, len(chunks) - index) * 0.01
        ranked.append((score, chunk))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return _select_diverse_chunks([chunk for _, chunk in ranked], limit)


def _question_keywords(question: str) -> list[str]:
    candidates = [
        "热氧老化", "紫外老化", "滑动磨损", "往复摩擦", "磨损", "裂纹", "剥落",
        "60 n", "160 m", "硬度", "磨损量", "载荷", "温度", "滑动距离",
        "高温摩擦", "摩擦系数", "热衰退", "摩擦膜", "氧化",
        "冲击", "低速冲击", "凹痕", "dent", "分层", "delamination",
        "无损检测", "c 扫", "基体开裂", "纤维断裂",
    ]
    normalized = question.lower()
    return [keyword for keyword in candidates if keyword in normalized]


def _explanation_level(profile: dict) -> str:
    learner_type = profile.get("learner_type", "")
    if "本科" in learner_type:
        return "现象引导与基础机理链"
    if "研究生" in learner_type:
        return "变量控制、多源证据与可证伪机理"
    if "机务" in learner_type or "维修" in learner_type:
        return "检查流程、风险分级与升级报告边界"
    return "依据当前画像动态适配"


def _adaptation_sentence(learner_type: str, weak_points: str) -> str:
    if "本科" in learner_type:
        return f"你当前的薄弱点是 {weak_points}，先按“现象—工况—材料变化—待补证据”四步理解，不要求一次给出完整机理。"
    if "研究生" in learner_type:
        return f"围绕 {weak_points}，应明确自变量、控制变量、竞争机理和可证伪的验证手段。"
    if "机务" in learner_type or "维修" in learner_type:
        return f"围绕 {weak_points}，优先记录损伤位置、尺寸、趋势和限制条件，再依据适用文件决定是否升级检查。"
    return f"围绕 {weak_points}，按当前诊断水平逐步建立证据链。"


def _default_boundaries(domain: str) -> list[str]:
    boundaries = [
        "形貌和单一指标只能支持受限推断，不能独立证明完整损伤机理。",
        "未在证据中记录的工况、数值和实验参数保持未知，不进行插补。",
    ]
    if domain in {"tire", "brake", "composite"}:
        boundaries.append("训练输出不能替代维修手册、工卡、适航要求和授权人员放行。")
    return boundaries


def _follow_up_question(context: dict[str, Any]) -> str:
    domain_questions = {
        "tire": "为了区分热氧老化、机械磨损及其耦合作用，你还需要补充哪两类表征证据？",
        "brake": "若摩擦系数下降同时出现氧化和裂纹，你会怎样区分热衰退现象与失效原因？",
        "composite": "为什么表面轻微凹痕不能排除层间分层，你会优先选择哪种无损检测手段？",
    }
    return domain_questions[context["domain"]]


def _normalize_action(value: Any, context: dict[str, Any]) -> str:
    allowed = {"降维解释", "继续巩固", "补充案例", "进阶挑战"}
    if value in allowed:
        return str(value)
    score = context["diagnosis_result"].score
    question = context["inquiry_question"]
    if score < 50:
        return "降维解释"
    if any(keyword in question for keyword in ("为什么", "机理", "区别", "区分", "判断")):
        return "补充案例"
    if score >= 90:
        return "进阶挑战"
    return "继续巩固"
