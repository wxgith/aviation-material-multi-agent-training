from collections import defaultdict

from app.models.schemas import DiagnosisResult, QuestionDiagnosisDetail, TrainingDomain
from app.services.data_loader import get_profile, get_questions_by_domain


def evaluate_diagnosis(
    profile_id: str,
    domain: TrainingDomain,
    answers: list,
    profile_override: dict | None = None,
) -> DiagnosisResult:
    profile = profile_override or get_profile(profile_id)
    questions = get_questions_by_domain(domain)
    answer_map = {answer.question_id: answer.answer for answer in answers}

    correct_count = 0
    point_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
    details: list[QuestionDiagnosisDetail] = []

    for question in questions:
        learner_answer = answer_map.get(question["id"])
        is_correct = learner_answer == question["answer"]
        if is_correct:
            correct_count += 1

        point = question["knowledge_point"]
        point_stats[point]["total"] += 1
        if is_correct:
            point_stats[point]["correct"] += 1

        details.append(
            QuestionDiagnosisDetail(
                question_id=question["id"],
                knowledge_point=point,
                correct=is_correct,
                learner_answer=learner_answer,
                correct_answer=question["answer"],
                explanation=question["explanation"],
            )
        )

    total = len(questions) or 1
    score = round(correct_count / total * 100)
    level = _level_from_score(score)
    weak_points = [
        point for point, stat in point_stats.items()
        if stat["correct"] < stat["total"]
    ]
    strong_points = [
        point for point, stat in point_stats.items()
        if stat["correct"] == stat["total"]
    ]

    if not weak_points:
        weak_points = ["综合迁移应用"]

    summary = _build_summary(profile["learner_type"], score, level, weak_points, strong_points)
    return DiagnosisResult(
        profile_id=profile_id,
        domain=domain,
        score=score,
        level=level,
        weak_points=weak_points,
        strong_points=strong_points,
        diagnosis_summary=summary,
        details=details,
    )


def _level_from_score(score: int) -> str:
    if score < 60:
        return "基础薄弱"
    if score < 85:
        return "基础一般"
    return "掌握较好"


def _build_summary(
    learner_type: str,
    score: int,
    level: str,
    weak_points: list[str],
    strong_points: list[str],
) -> str:
    weak_text = "、".join(weak_points)
    strong_text = "、".join(strong_points) if strong_points else "暂无稳定优势点"
    return (
        f"{learner_type}本次诊断得分 {score} 分，水平判定为“{level}”。"
        f"当前薄弱点集中在 {weak_text}；相对优势为 {strong_text}。"
    )
