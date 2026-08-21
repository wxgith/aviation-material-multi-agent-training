from app.agents.base_agent import BaseAgent
from app.models.schemas import AgentStep, DiagnosisResult


class DiagnosisAgent(BaseAgent):
    agent_name = "学情诊断 Agent"
    role = "读取学习者画像和诊断结果，识别基础水平、强项与知识薄弱点。"

    def run(self, context: dict) -> AgentStep:
        diagnosis: DiagnosisResult = context["diagnosis_result"]
        profile = context["profile"]
        context["weak_points"] = diagnosis.weak_points
        context["strong_points"] = diagnosis.strong_points

        return self.step(
            input_summary=f"{profile['learner_type']}，诊断得分 {diagnosis.score}，自评 {profile['self_level']}",
            output_summary=diagnosis.diagnosis_summary,
            confidence=0.94,
            evidence_ids=[detail.question_id for detail in diagnosis.details],
            details={
                "score": diagnosis.score,
                "level": diagnosis.level,
                "weak_points": diagnosis.weak_points,
                "strong_points": diagnosis.strong_points,
                "profile_snapshot": profile,
            },
        )
