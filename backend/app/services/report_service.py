from app.models.schemas import DiagnosisResult, FeedbackRequest, FeedbackResponse
from app.db.repositories import persist_feedback


def build_report(session: dict) -> dict:
    diagnosis: DiagnosisResult = session["diagnosis_result"]
    resources = session["resources"]
    decision = session["decision"]
    review = session["review"]

    return {
        "session_id": session["session_id"],
        "profile": session["profile"],
        "domain": session["domain_info"],
        "diagnosis_score": diagnosis.score,
        "diagnosis_level": diagnosis.level,
        "knowledge_blind_spots": diagnosis.weak_points,
        "strong_points": diagnosis.strong_points,
        "diagnosis_summary": diagnosis.diagnosis_summary,
        "resource_difficulty_match": resources["difficulty_match"],
        "personalization_strategy": resources.get("personalization", {}),
        "recommended_learning_path": decision["learning_path"],
        "next_training_suggestion": decision["next_training_plan"],
        "recommended_action": decision["recommended_action"],
        "agent_review": review,
        "retrieved_knowledge": session.get("retrieved_chunks", []),
        "guided_inquiries": session.get("inquiry_history", []),
        "feedback_history": session.get("feedback_history", []),
    }


def build_export_markdown(session: dict) -> str:
    diagnosis: DiagnosisResult = session["diagnosis_result"]
    profile = session["profile"]
    domain = session["domain_info"]
    resources = session["resources"]
    review = session["review"]
    decision = session["decision"]
    chunks = session.get("retrieved_chunks", [])
    agent_steps = session.get("agent_steps", [])
    inquiries = session.get("inquiry_history", [])
    feedback_history = session.get("feedback_history", [])

    lines = [
        "# 面向航空工程材料损伤分析的多智能体个性化知识生成与实操训练系统",
        "",
        "## 1. 学习者画像",
        f"- 画像名称：{profile['name']}",
        f"- 学习者类型：{profile['learner_type']}",
        f"- 专业背景：{profile['background']}",
        f"- 画像特点：{profile['characteristics']}",
        f"- 自评基础：{profile['self_level']}",
        "",
        "## 2. 训练任务",
        f"- 训练方向：{domain['title']}",
        f"- 学习目标：{session['learning_goal']}",
        "",
        "## 3. 学情诊断结果",
        f"- 诊断得分：{diagnosis.score}",
        f"- 水平判定：{diagnosis.level}",
        f"- 知识薄弱点：{_join(diagnosis.weak_points)}",
        f"- 相对强项：{_join(diagnosis.strong_points)}",
        f"- 诊断摘要：{diagnosis.diagnosis_summary}",
        "",
        "## 4. Agent 协同过程摘要",
    ]

    for index, step in enumerate(agent_steps, start=1):
        lines.extend(
            [
                f"### {index}. {step.agent_name}",
                f"- 职责：{step.role}",
                f"- 输入：{step.input_summary}",
                f"- 输出：{step.output_summary}",
                f"- 置信度：{round(step.confidence * 100)}%",
                f"- 依据片段：{_join(step.evidence_ids)}",
                "",
            ]
        )

    lines.extend(["## 5. 检索知识依据"])
    for chunk in chunks:
        lines.extend(
            [
                f"### {chunk['id']} {chunk['title']}",
                f"- 标签：{_join(chunk.get('tags', []))}",
                f"- 难度：{chunk.get('difficulty', '')}",
                f"- 来源类型：{chunk.get('source_type', '')}",
                f"- 内容：{chunk.get('content', '')}",
                "",
            ]
        )

    lecture = resources["personalized_lecture"]
    personalization = resources.get("personalization", {})
    lines.extend(
        [
            "## 6. 个性化讲义",
            f"- 标题：{lecture['title']}",
            f"- 难度：{lecture['difficulty']}",
            f"- 目标：{lecture['target']}",
            f"- 画像策略：{personalization.get('strategy_label', '通用策略')}",
            f"- 讲解方式：{personalization.get('explanation_style', '按学情组织内容')}",
            f"- 实操重点：{personalization.get('practice_focus', '完成证据链训练')}",
        ]
    )
    for section in lecture["sections"]:
        lines.extend([f"### {section['heading']}", section["content"], ""])

    guide = resources["practical_guide"]
    lines.extend(["## 7. 实操指南", f"- 标题：{guide['title']}", ""])
    for index, step in enumerate(guide["steps"], start=1):
        lines.append(f"{index}. {step}")
    lines.extend(["", f"- 记录模板：{_join(guide['record_template'])}", ""])

    lines.extend(["## 8. 分阶测试题"])
    for item in resources["graded_quiz"]:
        lines.extend(
            [
                f"### {item['level']}：{item['knowledge_point']}",
                f"- 题目：{item['question']}",
                f"- 选项：{_join(item['options'])}",
                f"- 标准答案：{item['answer']}",
                f"- 解析：{item['explanation']}",
                "",
            ]
        )

    case_task = resources["case_task"]
    lines.extend(
        [
            "## 9. 案例分析任务",
            f"- 标题：{case_task['title']}",
            f"- 任务：{case_task['brief']}",
            f"- 关注点：{_join(case_task['focus_points'])}",
            f"- 预期输出：{_join(case_task['expected_output'])}",
            "",
            "## 10. 专家审核纠偏意见",
            f"- 审核状态：{review['status']}",
            f"- 一致性检查：{review['consistency_check']}",
            f"- 证据充分性：{review.get('evidence_sufficiency', '历史会话未记录')}",
            f"- 是否降级输出：{'是' if review.get('degraded_output') else '否'}",
            "- 风险点：",
        ]
    )
    lines.extend([f"  - {item}" for item in review["risk_points"]])
    lines.append("- 纠偏建议：")
    lines.extend([f"  - {item}" for item in review["corrections"]])
    lines.append("- 已验证声明：")
    lines.extend([f"  - {item}" for item in review.get("verified_claims", [])] or ["  - 无"])
    lines.append("- 不支持的越界声明：")
    lines.extend([f"  - {item}" for item in review.get("unsupported_claims", [])] or ["  - 无"])
    lines.append("- 证据缺口：")
    lines.extend([f"  - {item}" for item in review.get("evidence_gaps", [])] or ["  - 无"])

    lines.extend(
        [
            "",
            "## 11. 推荐学习路径",
        ]
    )
    for index, item in enumerate(decision["learning_path"], start=1):
        lines.append(f"{index}. {item}")
    lines.extend(
        [
            "",
            "## 12. 下一步训练建议",
            f"- 推荐动作：{decision['recommended_action']}",
            f"- 训练建议：{decision['next_training_plan']}",
            "",
            "## 13. 启发式动态追问记录",
        ]
    )
    if not inquiries:
        lines.extend(["- 当前会话尚未提交动态追问。", ""])
    for index, inquiry in enumerate(inquiries, start=1):
        audit = inquiry.get("generation_audit", {})
        inquiry_review = inquiry.get("review", {})
        lines.extend(
            [
                f"### 13.{index} {inquiry.get('question', '')}",
                f"- 生成模式：{inquiry.get('generation_mode', '')}",
                f"- 模型：{audit.get('model', 'mock-template')}",
                f"- 提示词版本：{audit.get('prompt_version', '')}",
                f"- 调用延迟：{audit.get('latency_ms', 0)} ms",
                f"- 检索模式：{inquiry.get('retrieval_mode', '')}",
                f"- 知识来源：{inquiry.get('knowledge_source', '')}",
                f"- 证据 ID：{_join(inquiry.get('evidence_ids', []))}",
                f"- 审核状态：{inquiry_review.get('status', '')}",
                f"- 下一动作：{inquiry.get('next_action', '')}",
                "",
                "**回答：**",
                inquiry.get("answer", ""),
                "",
                "**适用边界：**",
            ]
        )
        lines.extend([f"- {item}" for item in inquiry.get("boundaries", [])])
        lines.extend(
            [
                "",
                f"- 启发式追问：{inquiry.get('follow_up_question', '')}",
                f"- 实操任务：{inquiry.get('practice_task', '')}",
                "",
            ]
        )
    lines.extend(["## 14. 反馈迭代记录"])
    if not feedback_history:
        lines.extend(["- 当前会话尚未提交反馈测试。", ""])
    for index, feedback in enumerate(feedback_history, start=1):
        lines.extend(
            [
                f"### 14.{index} 第 {index} 轮反馈",
                f"- 反馈得分：{feedback.get('feedback_score', '')}",
                f"- 学习者反馈：{feedback.get('self_feedback', '') or '未填写'}",
                f"- 决策动作：{feedback.get('next_action', '')}",
                f"- 决策说明：{feedback.get('explanation', '')}",
                f"- 更新后路径：{_join(feedback.get('updated_learning_path', []))}",
                "",
            ]
        )
    lines.extend(
        [
            "## 15. PDF 生成提示",
            "可在浏览器或 Markdown 编辑器中打开本报告，使用打印功能另存为 PDF。",
            "",
        ]
    )
    return "\n".join(lines)


def evaluate_feedback(session: dict, request: FeedbackRequest) -> FeedbackResponse:
    quiz = session["resources"].get("graded_quiz", [])
    answer_map = {answer.question_id: answer.answer for answer in request.answers}
    correct = 0
    for item in quiz:
        if answer_map.get(item["id"]) == item["answer"]:
            correct += 1

    total = len(quiz) or 1
    score = round(correct / total * 100)
    action, explanation = _feedback_action(score, request.self_feedback)
    session.setdefault("feedback_history", []).append(
        {
            "feedback_score": score,
            "next_action": action,
            "self_feedback": request.self_feedback,
        }
    )
    from app.agents.orchestrator import orchestrator

    iteration_steps = orchestrator.iterate(
        session=session,
        feedback_action=action,
        feedback_explanation=explanation,
        self_feedback=request.self_feedback,
    )
    updated_path = session["decision"]["learning_path"]

    response = FeedbackResponse(
        feedback_score=score,
        next_action=action,
        explanation=explanation,
        updated_learning_path=updated_path,
        updated_resources=session["resources"],
        iteration_agent_steps=iteration_steps,
    )
    session["last_feedback_persisted"] = persist_feedback(
        session["session_id"],
        response,
        request.self_feedback,
    )
    return response


def _feedback_action(score: int, self_feedback: str) -> tuple[str, str]:
    feedback_note = f" 学习者反馈：{self_feedback}" if self_feedback else ""
    if score < 50:
        return "降维解释", f"反馈测试正确率偏低，建议回到核心概念，用更直观案例重新解释。{feedback_note}"
    if score < 75:
        return "补充案例", f"已具备部分理解，但迁移不足，建议补充同类案例并继续巩固。{feedback_note}"
    if score < 90:
        return "继续巩固", f"掌握较稳定，建议继续完成一轮证据链表达训练。{feedback_note}"
    return "进阶挑战", f"反馈表现较好，可进入耦合因素或复杂工况挑战任务。{feedback_note}"


def _join(items: list) -> str:
    return "、".join(str(item) for item in items) if items else "无"
