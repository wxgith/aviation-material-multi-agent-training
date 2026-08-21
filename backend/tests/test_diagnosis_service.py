from app.models.schemas import AnswerSubmission
from app.services.diagnosis_service import evaluate_diagnosis
from app.services.data_loader import get_questions_by_domain


def test_diagnosis_scoring_identifies_weak_points():
    questions = get_questions_by_domain("tire")
    answers = [
        AnswerSubmission(question_id=questions[0]["id"], answer=questions[0]["answer"]),
        AnswerSubmission(question_id=questions[1]["id"], answer=questions[1]["answer"]),
        AnswerSubmission(question_id=questions[2]["id"], answer=questions[2]["answer"]),
        AnswerSubmission(question_id=questions[3]["id"], answer="图片是否足够美观"),
        AnswerSubmission(question_id=questions[4]["id"], answer="正确"),
    ]

    result = evaluate_diagnosis("undergrad_basic", "tire", answers)

    assert result.score == 60
    assert result.level == "基础一般"
    assert any("耦合损伤" in point for point in result.weak_points)
    assert "常见误区" in result.weak_points
