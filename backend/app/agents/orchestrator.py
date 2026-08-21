from app.agents.decision_agent import DecisionAgent
from app.agents.diagnosis_agent import DiagnosisAgent
from app.agents.generation_agent import GenerationAgent
from app.agents.material_router_agent import MaterialRouterAgent
from app.agents.retrieval_agent import RetrievalAgent
from app.agents.review_agent import ReviewAgent
from app.db.repositories import persist_agent_iteration, persist_agent_session
from app.models.schemas import AgentRunRequest
from app.services.data_loader import get_profile
from app.services.session_store import session_store
from app.services.task_manager import TaskCancelled


class AgentOrchestrator:
    def __init__(self) -> None:
        self.diagnosis_agent = DiagnosisAgent()
        self.router_agent = MaterialRouterAgent()
        self.retrieval_agent = RetrievalAgent()
        self.generation_agent = GenerationAgent()
        self.review_agent = ReviewAgent()
        self.decision_agent = DecisionAgent()
        self.agents = [
            self.diagnosis_agent,
            self.router_agent,
            self.retrieval_agent,
            self.generation_agent,
            self.review_agent,
            self.decision_agent,
        ]

    def run(self, request: AgentRunRequest, progress_callback=None, cancel_check=None) -> dict:
        emit = progress_callback or (lambda *_args, **_kwargs: None)
        cancelled = cancel_check or (lambda: False)
        profile = (
            request.profile_override.model_dump()
            if request.profile_override is not None
            else get_profile(request.profile_id)
        )
        context = {
            "profile": profile,
            "domain": request.domain,
            "diagnosis_result": request.diagnosis_result,
            "learning_goal": request.learning_goal,
        }
        steps = []
        total_steps = len(self.agents)
        for index, agent in enumerate(self.agents):
            if cancelled():
                raise TaskCancelled()
            emit(
                "agent_started",
                progress=max(4, round(index / total_steps * 90)),
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
                progress=round((index + 1) / total_steps * 90),
                message=f"已完成：{agent.agent_name}",
                detail=step.output_summary,
                current_agent=agent.agent_name,
                step_index=index + 1,
                total_steps=total_steps,
                agent_step=step.model_dump(),
            )

        if context["review"].get("requires_regeneration"):
            if cancelled():
                raise TaskCancelled()
            first_review = context["review"]
            context["review_retry"] = True
            context["correction_guidance"] = first_review.get("rejection_reasons", [])
            emit(
                "regeneration_started",
                progress=77,
                message="审核未通过，正在纠偏重生",
                detail="资源生成 Agent 将依据审核意见重新生成，并再次交由审核 Agent 核验。",
                current_agent=self.generation_agent.agent_name,
                step_index=4,
                total_steps=total_steps,
            )
            steps[3] = self.generation_agent.run(context)
            if cancelled():
                raise TaskCancelled()
            steps[4] = self.review_agent.run(context)
            steps[4].details["correction_rounds"] = 1
            steps[4].details["initial_review"] = first_review

        session = {
            "profile": context["profile"],
            "domain": request.domain,
            "domain_info": context["domain_info"],
            "diagnosis_result": request.diagnosis_result,
            "learning_goal": request.learning_goal,
            "retrieved_chunks": context["retrieved_chunks"],
            "retrieval_source": context.get("retrieval_source", "local-json"),
            "retrieval_mode": context.get("retrieval_mode", "hybrid"),
            "resources": context["resources"],
            "review": context["review"],
            "decision": context["decision"],
            "agent_steps": steps,
            "feedback_history": [],
            "inquiry_history": [],
        }
        if cancelled():
            raise TaskCancelled()
        emit(
            "persisting",
            progress=95,
            message="正在保存训练会话",
            detail="将 Agent 步骤、生成资源和学情报告写入持久化存储。",
            current_agent="会话持久化",
            step_index=total_steps,
            total_steps=total_steps,
        )
        created_session = session_store.create(session)
        created_session["persistence"] = {
            "database_written": persist_agent_session(created_session)
        }
        return created_session

    def iterate(
        self,
        session: dict,
        feedback_action: str,
        feedback_explanation: str,
        self_feedback: str,
    ) -> list:
        previous_path = list(session["decision"].get("learning_path", []))
        context = {
            "profile": session["profile"],
            "domain": session["domain"],
            "domain_info": session["domain_info"],
            "diagnosis_result": session["diagnosis_result"],
            "learning_goal": session["learning_goal"],
            "weak_points": session["diagnosis_result"].weak_points,
            "strong_points": session["diagnosis_result"].strong_points,
            "feedback_action": feedback_action,
            "feedback_explanation": feedback_explanation,
            "self_feedback": self_feedback,
        }
        steps = [
            self.retrieval_agent.run(context),
            self.generation_agent.run(context),
            self.review_agent.run(context),
        ]
        if context["review"].get("requires_regeneration"):
            first_review = context["review"]
            context["review_retry"] = True
            context["correction_guidance"] = first_review.get("rejection_reasons", [])
            steps[1] = self.generation_agent.run(context)
            steps[2] = self.review_agent.run(context)
            steps[2].details["correction_rounds"] = 1
            steps[2].details["initial_review"] = first_review
        steps.append(self.decision_agent.run(context))

        context["decision"]["learning_path"] = previous_path + [f"反馈迭代：{feedback_action}"]
        steps[-1].details = context["decision"]
        session.update(
            {
                "retrieved_chunks": context["retrieved_chunks"],
                "retrieval_source": context.get("retrieval_source", "local-json"),
                "retrieval_mode": context.get("retrieval_mode", "hybrid"),
                "resources": context["resources"],
                "review": context["review"],
                "decision": context["decision"],
            }
        )
        session.setdefault("iteration_steps", []).append(steps)
        persist_agent_iteration(session, steps)
        return steps


orchestrator = AgentOrchestrator()
