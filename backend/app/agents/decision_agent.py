from app.agents.base_agent import BaseAgent
from app.models.schemas import AgentStep


class DecisionAgent(BaseAgent):
    agent_name = "学习路径决策 Agent"
    role = "根据诊断结果、资源难度和审核意见输出学习路径、训练建议和推荐动作。"

    def run(self, context: dict) -> AgentStep:
        diagnosis = context["diagnosis_result"]
        resources = context["resources"]
        feedback_action = context.get("feedback_action")
        if feedback_action:
            action = feedback_action
            plan = context.get("feedback_explanation") or _plan_for_feedback(
                feedback_action, diagnosis.weak_points
            )
        else:
            action, plan = _action_from_score(diagnosis.score, diagnosis.weak_points)
        path = [
            "画像确认",
            "基础概念校准",
            "典型损伤识别",
            "机理证据链分析",
            "实操检查任务",
            "反馈测试与动态更新",
        ]

        decision = {
            "learning_path": path,
            "difficulty_match": resources["difficulty_match"],
            "next_training_plan": plan,
            "recommended_action": action,
        }
        context["decision"] = decision

        return self.step(
            input_summary=f"score={diagnosis.score}，level={diagnosis.level}",
            output_summary=f"推荐动作：{action}；下一步：{plan}",
            confidence=0.91,
            evidence_ids=context["review"]["evidence_ids"],
            details=decision,
        )


def _action_from_score(score: int, weak_points: list[str]) -> tuple[str, str]:
    weak_text = "、".join(weak_points)
    if score < 50:
        return "降维解释", f"先用低门槛案例解释 {weak_text}，再重新完成基础测试。"
    if score < 75:
        return "补充案例 + 继续巩固", f"围绕 {weak_text} 追加胎面裂纹/剥落或对应方向案例，并继续巩固证据链表达。"
    if score < 90:
        return "继续巩固", f"完成同方向实操指南和分阶测试，重点提升 {weak_text} 的迁移能力。"
    return "进阶挑战", f"进入多因素耦合分析任务，训练 {weak_text} 的边界构建和决策表达。"


def _plan_for_feedback(action: str, weak_points: list[str]) -> str:
    weak_text = "、".join(weak_points)
    plans = {
        "降维解释": f"回到 {weak_text} 的可观察现象和基础概念，完成一次低门槛重测。",
        "补充案例": f"围绕 {weak_text} 增加对比案例，训练从证据到机理的迁移判断。",
        "继续巩固": f"继续完成 {weak_text} 的证据链表达与实操记录训练。",
        "进阶挑战": f"进入 {weak_text} 的多因素耦合和边界条件挑战任务。",
    }
    return plans.get(action, f"继续围绕 {weak_text} 开展针对性训练。")
