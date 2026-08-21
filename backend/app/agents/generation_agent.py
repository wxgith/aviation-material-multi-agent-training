from app.agents.base_agent import BaseAgent
from app.models.schemas import AgentStep
from app.services.resource_service import generate_resources


class GenerationAgent(BaseAgent):
    agent_name = "个性化资源生成 Agent"
    role = "根据学习者画像、诊断结果和检索证据生成讲义、实操指南、分阶测试题和案例任务。"

    def run(self, context: dict) -> AgentStep:
        resources = generate_resources(
            profile=context["profile"],
            domain=context["domain"],
            diagnosis=context["diagnosis_result"],
            retrieved_chunks=context["retrieved_chunks"],
            learning_goal=context["learning_goal"],
            feedback_action=context.get("feedback_action"),
            correction_guidance=context.get("correction_guidance"),
        )
        context["resources"] = resources
        evidence_ids = list(
            dict.fromkeys(
                evidence_id
                for section in resources["personalized_lecture"].get("sections", [])
                for evidence_id in section.get("evidence_ids", [])
            )
        )

        return self.step(
            input_summary=f"{context['profile']['learner_type']}；资源难度={resources['difficulty_match']['resource_difficulty']}",
            output_summary=(
                "已生成个性化讲义、实操训练指南、分阶测试题和案例分析任务；"
                f"生成模式={resources.get('generation_mode', 'mock-template')}。"
            ),
            confidence=0.86,
            evidence_ids=evidence_ids,
            details={
                "resource_keys": list(resources.keys()),
                "difficulty_match": resources["difficulty_match"],
                "personalization": resources.get("personalization", {}),
                "evidence_boundary": resources.get("evidence_boundary", {}),
                "generation_mode": resources.get("generation_mode", "mock-template"),
                "generation_audit": resources.get("generation_audit", {}),
                "llm_error": resources.get("llm_error", ""),
            },
        )
