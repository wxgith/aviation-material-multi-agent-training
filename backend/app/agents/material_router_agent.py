from app.agents.base_agent import BaseAgent
from app.models.schemas import AgentStep
from app.services.data_loader import get_knowledge_domain


class MaterialRouterAgent(BaseAgent):
    agent_name = "材料领域路由 Agent"
    role = "根据训练方向选择航空轮胎、航空刹车片或复合材料板知识库。"

    def run(self, context: dict) -> AgentStep:
        domain = context["domain"]
        domain_info = get_knowledge_domain(domain)
        context["domain_info"] = {
            "domain": domain_info["domain"],
            "title": domain_info["title"],
            "summary": domain_info["summary"],
        }

        return self.step(
            input_summary=f"domain={domain}",
            output_summary=f"已路由到“{domain_info['title']}”知识库。",
            confidence=0.98,
            evidence_ids=[],
            details=context["domain_info"],
        )
