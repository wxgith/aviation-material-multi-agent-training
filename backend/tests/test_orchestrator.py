from app.agents.orchestrator import orchestrator
from app.models.schemas import AgentRunRequest, AnswerSubmission
from app.services.data_loader import get_profile, get_questions_by_domain
from app.services.diagnosis_service import evaluate_diagnosis


def test_orchestrator_outputs_six_agent_steps():
    profile = get_profile("undergrad_basic")
    questions = get_questions_by_domain("tire")
    answers = [
        AnswerSubmission(question_id=question["id"], answer=question["answer"])
        for question in questions
    ]
    diagnosis = evaluate_diagnosis("undergrad_basic", "tire", answers)
    session = orchestrator.run(
        AgentRunRequest(
            profile_id="undergrad_basic",
            domain="tire",
            diagnosis_result=diagnosis,
            learning_goal=profile["default_goal"],
        )
    )

    assert session["session_id"]
    assert len(session["agent_steps"]) == 6
    assert session["resources"]["personalized_lecture"]
    assert session["review"]["status"]
    assert session["decision"]["learning_path"]
