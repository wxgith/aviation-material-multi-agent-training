import re
from typing import Callable

from app.agents.inquiry_orchestrator import guided_inquiry_orchestrator
from app.models.schemas import DiagnosisResult, InterfaceAssistantRequest
from app.services.data_loader import get_profile


VIEW_GUIDES = {
    "home": "首页用于确认系统运行模式并选择入口。首次体验建议点击“加载演示案例”，系统会自动填入画像、方向、目标和诊断答案。",
    "knowledge": "知识证据库用于查看来源、实验卡、切片数量、证据 ID 与适用边界，可按领域和关键词筛选。",
    "history": "历史训练会话用于恢复 MySQL 中已保存的画像、诊断、Agent 步骤、资源、问答和报告。",
    "profile": "画像输入页用于设置学习者类型、专业背景、训练方向、自评基础和当前目标，这些字段会影响讲解深度与任务形式。",
    "diagnosis": "学情诊断页通过方向化题目识别薄弱点。提交后会启动诊断、路由、检索、生成、审核和决策 Agent。",
    "agents": "多智能体协同页展示 6 个 Agent 的输入、输出、置信度、证据 ID 和检索来源，适合核对系统是否真正形成闭环。",
    "resources": "资源生成页展示个性化讲义、实操指南、分阶测试题和案例任务，内容难度由画像与诊断结果共同决定。",
    "inquiry": "智能训练工作台支持围绕当前会话继续追问，回答会绑定检索证据并经过审核纠偏。",
    "report": "学情报告页汇总得分、知识盲区、难度匹配、审核意见、学习路径和下一步训练建议。",
    "feedback": "反馈迭代页根据测试正确率决定降维解释、继续巩固、补充案例或进阶挑战。",
}

VIEW_QUESTIONS = {
    "home": ["我第一次使用应该从哪里开始？", "三个训练方向有什么区别？", "演示案例会展示哪些能力？"],
    "diagnosis": ["这些题目如何影响后续资源？", "当前诊断重点是什么？", "提交后有哪些 Agent 工作？"],
    "agents": ["检索 Agent 使用了哪些证据？", "审核 Agent 检查了哪些风险？", "为什么推荐当前学习路径？"],
    "resources": ["这份讲义为什么适合当前画像？", "实操指南中哪些步骤最关键？", "请解释案例任务的证据链。"],
    "report": ["当前最主要的知识盲区是什么？", "为什么匹配这个资源难度？", "下一步训练应该如何安排？"],
    "feedback": ["反馈分数如何决定下一动作？", "什么时候适合进入进阶挑战？", "怎样判断需要补充案例？"],
}

VIEW_ACTION_GUIDES = {
    "demo": ("点击首页主操作区的“加载演示案例”，系统会自动填充画像、航空轮胎方向、学习目标和诊断答案。", "home"),
    "export": ("完成 Agent 管线后进入“学情报告”页，点击“导出学情报告”即可下载 Markdown 报告，也可用浏览器打印为 PDF。", "report"),
    "history": ("进入“历史训练会话”，可按关键词或训练方向筛选，并恢复 MySQL 中已保存的完整训练记录。", "history"),
    "feedback": ("进入“反馈迭代”页完成资源中的分阶测试并提交自评，系统会更新下一动作和学习路径。", "feedback"),
    "evidence": ("进入“知识证据库”可筛选来源与实验卡；在“多智能体协同”页可查看本轮 RetrievalAgent 返回的证据 ID、标题和检索来源。", "knowledge"),
}


def run_interface_assistant(
    request: InterfaceAssistantRequest,
    session: dict | None = None,
    progress_callback: Callable | None = None,
    cancel_check: Callable | None = None,
) -> dict:
    question = request.question.strip()
    context = request.context.model_dump()
    active_view = context.get("active_view") or "home"
    emit = progress_callback or (lambda *_args, **_kwargs: None)

    if _is_interface_question(question):
        emit(
            "agent_started",
            progress=25,
            message="正在理解当前界面",
            detail="读取页面、训练方向和当前会话状态。",
            current_agent="界面理解 Agent",
            step_index=1,
            total_steps=2,
        )
        guide = VIEW_GUIDES.get(active_view, VIEW_GUIDES["home"])
        recommended_view = _recommended_view(question, active_view)
        answer = _interface_guide_answer(question, guide)
        if recommended_view and recommended_view != active_view:
            answer += f" 根据你的问题，建议下一步前往“{_view_label(recommended_view)}”。"
        emit(
            "agent_completed",
            progress=72,
            message="界面引导已生成",
            detail="已结合当前页面给出操作建议。",
            current_agent="导航决策 Agent",
            step_index=2,
            total_steps=2,
        )
        return {
            "answer": answer,
            "answer_type": "interface-guide",
            "context_summary": _context_summary(context),
            "evidence_ids": [],
            "evidence_titles": [],
            "boundaries": ["本回答基于前端传递的结构化页面状态，不读取屏幕外信息。"],
            "suggested_questions": _suggested_questions(active_view),
            "recommended_view": recommended_view,
            "generation_mode": "ui-guide-rules",
            "knowledge_source": "interface-context",
            "agent_steps": [
                _step("界面理解 Agent", "识别当前页面及可用状态", _context_summary(context), 0.98),
                _step("导航决策 Agent", "匹配操作目标与系统入口", answer, 0.96),
            ],
        }

    if _is_context_status_question(question):
        emit(
            "agent_started",
            progress=34,
            message="正在读取当前训练状态",
            detail="核对页面、画像、诊断结果与当前会话。",
            current_agent="上下文理解 Agent",
            step_index=1,
            total_steps=2,
        )
        answer = _context_status_answer(question, context)
        emit(
            "agent_completed",
            progress=78,
            message="当前状态解释已生成",
            detail="回答仅使用当前页面已确认的信息。",
            current_agent="状态解释 Agent",
            step_index=2,
            total_steps=2,
        )
        return {
            "answer": answer,
            "answer_type": "context-summary",
            "context_summary": _context_summary(context),
            "evidence_ids": [],
            "evidence_titles": [],
            "boundaries": ["本回答只总结当前页面和已完成训练结果，不补造尚未产生的诊断或报告数据。"],
            "suggested_questions": _suggested_questions(active_view),
            "recommended_view": _recommended_view(question, active_view),
            "generation_mode": "context-rules",
            "knowledge_source": "page-context",
            "agent_steps": [
                _step("上下文理解 Agent", "读取当前训练状态", _context_summary(context), 0.98),
                _step("状态解释 Agent", "解释已确认的画像与学情信息", answer, 0.97),
            ],
        }

    working_session = session or _ephemeral_session(context)
    interaction = guided_inquiry_orchestrator.run(
        working_session,
        question,
        progress_callback=progress_callback,
        cancel_check=cancel_check,
        page_context=context,
        persist=session is not None,
    )
    return {
        "answer": interaction["answer"],
        "answer_type": "session-grounded" if session else "domain-grounded",
        "context_summary": _context_summary(context),
        "evidence_ids": interaction.get("evidence_ids", []),
        "evidence_titles": interaction.get("evidence_titles", []),
        "boundaries": interaction.get("boundaries", []),
        "suggested_questions": _suggested_questions(active_view),
        "recommended_view": _recommended_view(question, active_view),
        "generation_mode": interaction.get("generation_mode", "mock-template"),
        "knowledge_source": interaction.get("knowledge_source", "local-json"),
        "agent_steps": interaction.get("agent_steps", []),
    }


def _ephemeral_session(context: dict) -> dict:
    profile_id = context.get("profile_id") or "undergrad_basic"
    try:
        profile = get_profile(profile_id)
    except KeyError:
        profile = get_profile("undergrad_basic")
    domain = context.get("domain") or "tire"
    weak_points = context.get("weak_points") or _default_weak_points(domain)
    diagnosis = DiagnosisResult(
        profile_id=profile["profile_id"],
        domain=domain,
        score=context.get("diagnosis_score") if context.get("diagnosis_score") is not None else 60,
        level=context.get("diagnosis_level") or "待诊断",
        weak_points=weak_points,
        strong_points=context.get("strong_points") or [],
        diagnosis_summary="全局助手依据当前页面状态构建的临时训练上下文。",
        details=[],
    )
    return {
        "session_id": "assistant-preview",
        "profile": profile,
        "domain": domain,
        "diagnosis_result": diagnosis,
        "learning_goal": context.get("learning_goal") or profile.get("default_goal", ""),
        "inquiry_history": _recent_messages_as_history(context.get("recent_messages", [])),
    }


def _is_interface_question(question: str) -> bool:
    return bool(re.search(
        r"怎么开始|咋开始|如何开始|怎么用|咋用|如何使用|从哪里开始|在哪(?:里)?|哪个页面|什么按钮|"
        r"系统流程|系统功能|页面作用|当前页面|演示案例|三个训练方向|训练方向.{0,8}区别|有哪些训练方向|"
        r"怎么导出|咋导出|如何导出|导出报告|下载报告|查看历史|恢复(?:会话|训练|记录)|以前.*训练|查看证据|证据在哪|怎么反馈|提交反馈",
        question,
    ))


def _interface_guide_answer(question: str, default_guide: str) -> str:
    if re.search(r"三个训练方向|训练方向.{0,8}区别|有哪些训练方向", question):
        return (
            "系统包含三个训练方向：航空轮胎侧重热氧老化、摩擦磨损、裂纹与剥落判读；"
            "航空刹车片侧重高温摩擦、热衰退、氧化和失效机理；"
            "复合材料板侧重冲击损伤、分层、基体开裂、纤维断裂及无损检测图像判读。"
            "选择方向后，诊断题、检索知识库和生成资源都会同步切换。"
        )
    action = _interface_action(question)
    if action:
        return VIEW_ACTION_GUIDES[action][0]
    return default_guide


def _interface_action(question: str) -> str | None:
    patterns = (
        (r"演示案例|一键演示", "demo"),
        (r"导出|下载报告|打印.*PDF", "export"),
        (r"历史|恢复.*会话|以前.*训练", "history"),
        (r"反馈|正确率.*更新|下一动作.*更新", "feedback"),
        (r"证据在哪|查看证据|知识来源在哪|检索依据在哪", "evidence"),
    )
    for pattern, action in patterns:
        if re.search(pattern, question, re.IGNORECASE):
            return action
    return None


def _is_context_status_question(question: str) -> bool:
    # Explanations about evidence, mechanisms, or review decisions must use the
    # grounded multi-agent path instead of the lightweight page-state summary.
    if re.search(r"为什么|原因|审核|驳回|重生|纠偏|风险|依据|证据|机理|机制|解释|判断", question):
        return False
    subject = r"当前|我的|我这次|本次|这个|现在|我"
    status = r"得分|分数|多少分|薄弱|薄弱点|哪里不会|不会什么|盲区|强项|擅长|掌握|学习目标|目标是啥|训练方向|画像|会话|诊断结果|训练状态|下一步|接下来|学什么|练什么|先看什么|先做什么|建议"
    return bool(re.search(subject, question) and re.search(status, question))


def _context_status_answer(question: str, context: dict) -> str:
    answers: list[str] = []
    asks_feedback_score = bool(re.search(r"反馈.{0,6}(?:得分|分数|正确率)|刚才.{0,6}(?:得分|分数)", question))
    if re.search(r"薄弱|盲区|哪里不会|不会什么", question):
        weak_points = context.get("weak_points") or []
        if weak_points:
            answers.append(f"当前识别出的主要知识薄弱点是：{'、'.join(weak_points)}。")
        else:
            answers.append("当前还没有形成可确认的知识薄弱点。请先完成学情诊断，系统会根据错题知识点生成盲区清单。")
    if re.search(r"强项|掌握|擅长", question):
        strong_points = context.get("strong_points") or []
        if strong_points:
            answers.append(f"当前相对掌握较好的知识点是：{'、'.join(strong_points)}。")
        else:
            answers.append("当前页面还没有可确认的强项数据。完成诊断后，报告页会展示强项与薄弱点。")
    if asks_feedback_score:
        feedback_score = context.get("feedback_score")
        if feedback_score is not None:
            answers.append(f"最近一次反馈测试得分为 {feedback_score} 分。")
        else:
            answers.append("当前还没有已提交的反馈测试得分。")
    if re.search(r"诊断.{0,6}(?:得分|分数|结果)", question) or (
        re.search(r"得分|分数|多少分|诊断结果", question) and not asks_feedback_score
    ):
        score = context.get("diagnosis_score")
        level = context.get("diagnosis_level") or "尚未判定"
        if score is not None:
            answers.append(f"本次诊断得分为 {score} 分，当前水平为“{level}”。")
        else:
            answers.append("当前尚未提交诊断，因此还没有正式得分。请完成诊断题并提交，系统随后会启动 6 个 Agent 的协同流程。")
    if re.search(r"学习目标|目标是啥", question):
        goal = context.get("learning_goal") or "尚未设置"
        answers.append(f"当前学习目标是：{goal}。")
    if re.search(r"训练方向", question):
        domain_name = {"tire": "航空轮胎", "brake": "航空刹车片", "composite": "复合材料板"}.get(
            context.get("domain"), context.get("domain") or "尚未选择"
        )
        answers.append(f"当前训练方向是“{domain_name}”。知识检索和诊断题都会限制在该领域内。")
    if re.search(r"下一步|接下来|学什么|练什么|先看什么|先做什么|建议", question):
        weak_points = context.get("weak_points") or []
        if context.get("diagnosis_score") is None:
            answers.append("当前还没有正式诊断结果。建议先完成学情诊断，再由决策 Agent 根据得分和薄弱点生成学习路径。")
        else:
            action = context.get("recommended_action") or "完成当前页面对应的训练步骤"
            suggestion = context.get("next_training_suggestion") or ""
            weak_text = f"优先处理{'、'.join(weak_points)}，" if weak_points else ""
            next_text = f"下一步建议执行“{action}”：{weak_text}{suggestion}".rstrip("：")
            if not suggestion:
                next_text += "，再提交反馈测试确认是否进入进阶任务。"
            answers.append(next_text)
    if answers:
        return "\n\n".join(answers)
    return f"当前训练状态为：{_context_summary(context)}。{context.get('visible_summary') or ''}".strip()


def _recommended_view(question: str, current: str) -> str | None:
    action = _interface_action(question)
    if action:
        return VIEW_ACTION_GUIDES[action][1]
    routes = [
        (r"证据|知识库|文献|来源", "knowledge"),
        (r"画像|学习者信息", "profile"),
        (r"诊断|答题|测试", "diagnosis"),
        (r"Agent|智能体|协同|检索过程", "agents"),
        (r"讲义|实操|资源|案例任务", "resources"),
        (r"追问|问答|聊天", "inquiry"),
        (r"报告|学习路径|盲区", "report"),
        (r"反馈|正确率|进阶", "feedback"),
    ]
    for pattern, view in routes:
        if re.search(pattern, question, re.IGNORECASE):
            return view
    if re.search(r"开始|首次|演示", question):
        return "diagnosis"
    return current


def _recent_messages_as_history(messages: list[dict]) -> list[dict]:
    history: list[dict] = []
    pending_question = ""
    for item in messages[-6:]:
        role = str(item.get("role", ""))
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        if role == "user":
            pending_question = content
        elif role == "assistant" and pending_question:
            history.append({"question": pending_question, "answer": content})
            pending_question = ""
    return history[-2:]


def _suggested_questions(view: str) -> list[str]:
    return VIEW_QUESTIONS.get(view, VIEW_QUESTIONS["home"])


def _context_summary(context: dict) -> str:
    parts = [f"当前页面：{context.get('active_view_label') or _view_label(context.get('active_view', 'home'))}"]
    if context.get("learner_type"):
        parts.append(f"学习者：{context['learner_type']}")
    if context.get("diagnosis_score") is not None:
        parts.append(f"诊断得分：{context['diagnosis_score']}")
    if context.get("session_id"):
        parts.append("已绑定训练会话")
    return "；".join(parts)


def _view_label(view: str) -> str:
    labels = {
        "home": "首页", "knowledge": "知识证据库", "history": "历史训练会话",
        "profile": "画像输入", "diagnosis": "学情诊断", "agents": "多智能体协同",
        "resources": "资源生成", "inquiry": "智能训练工作台", "report": "学情报告",
        "feedback": "反馈迭代",
    }
    return labels.get(view, view)


def _default_weak_points(domain: str) -> list[str]:
    return {
        "tire": ["损伤机理", "实验表征"],
        "brake": ["高温摩擦", "失效机理"],
        "composite": ["冲击损伤", "无损检测"],
    }.get(domain, ["损伤机理"])


def _step(name: str, role: str, output: str, confidence: float) -> dict:
    return {
        "agent_name": name,
        "role": role,
        "input_summary": "当前页面上下文 + 用户问题",
        "output_summary": output,
        "status": "completed",
        "confidence": confidence,
        "evidence_ids": [],
        "details": {},
    }
