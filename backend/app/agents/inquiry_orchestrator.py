from uuid import uuid4

from app.agents.guided_inquiry_agents import (
    GuidedTutorAgent,
    InquiryDecisionAgent,
    InquiryReviewAgent,
)
from app.agents.material_router_agent import MaterialRouterAgent
from app.agents.retrieval_agent import RetrievalAgent
from app.db.repositories import persist_learning_interaction, persist_report_snapshot
from app.services.task_manager import TaskCancelled


class GuidedInquiryOrchestrator:
    def __init__(self) -> None:
        self.agents = [
            MaterialRouterAgent(),
            RetrievalAgent(),
            GuidedTutorAgent(),
            InquiryReviewAgent(),
            InquiryDecisionAgent(),
        ]

    def run(
        self,
        session: dict,
        question: str,
        progress_callback=None,
        cancel_check=None,
        page_context: dict | None = None,
        persist: bool = True,
    ) -> dict:
        emit = progress_callback or (lambda *_args, **_kwargs: None)
        cancelled = cancel_check or (lambda: False)
        recent_questions = [
            str(item.get("question", "")).strip()
            for item in session.get("inquiry_history", [])[-2:]
            if str(item.get("question", "")).strip()
        ]
        retrieval_goal = question
        if recent_questions:
            retrieval_goal += "；对话上下文：" + "；".join(recent_questions)
        context = {
            "profile": session["profile"],
            "domain": session["domain"],
            "diagnosis_result": session["diagnosis_result"],
            "weak_points": session["diagnosis_result"].weak_points,
            "strong_points": session["diagnosis_result"].strong_points,
            "learning_goal": retrieval_goal,
            "original_learning_goal": session["learning_goal"],
            "inquiry_question": question,
            "inquiry_history": session.get("inquiry_history", []),
            "page_context": page_context or {},
        }
        steps = []
        total_steps = len(self.agents)
        for index, agent in enumerate(self.agents):
            if cancelled():
                raise TaskCancelled()
            emit(
                "agent_started",
                progress=max(5, round(index / total_steps * 92)),
                message=f"正在执行：{agent.agent_name}",
                detail=agent.role,
                current_agent=agent.agent_name,
                step_index=index + 1,
                total_steps=total_steps,
            )
            step = agent.run(context)
            steps.append(step)
            emit(
                "agent_completed",
                progress=round((index + 1) / total_steps * 92),
                message=f"已完成：{agent.agent_name}",
                detail=step.output_summary,
                current_agent=agent.agent_name,
                step_index=index + 1,
                total_steps=total_steps,
                agent_step=step.model_dump(),
            )
        if cancelled():
            raise TaskCancelled()
        answer = context["inquiry_answer"]
        interaction = {
            "interaction_id": str(uuid4()),
            "session_id": session["session_id"],
            "question": question,
            "answer": answer["answer"],
            "explanation_level": answer["explanation_level"],
            "evidence_ids": answer["evidence_ids"],
            "evidence_titles": answer["evidence_titles"],
            "evidence_snippets": answer["evidence_snippets"],
            "boundaries": answer["boundaries"],
            "follow_up_question": answer["follow_up_question"],
            "practice_task": answer["practice_task"],
            "next_action": answer["next_action"],
            "generation_mode": answer["generation_mode"],
            "generation_audit": answer.get("generation_audit", {}),
            "retrieval_mode": context.get("retrieval_mode", "bm25"),
            "knowledge_source": context.get("retrieval_source", "local-json"),
            "review": context["inquiry_review"],
            "agent_steps": steps,
        }
        if persist:
            session.setdefault("inquiry_history", []).append(interaction)
            emit(
                "persisting",
                progress=96,
                message="正在保存本轮训练记录",
                detail="动态回答、证据链和审核结果将进入历史会话与学情报告。",
                current_agent="会话持久化",
                step_index=total_steps,
                total_steps=total_steps,
            )
            persist_learning_interaction(interaction)
            persist_report_snapshot(session)
        return interaction


guided_inquiry_orchestrator = GuidedInquiryOrchestrator()
