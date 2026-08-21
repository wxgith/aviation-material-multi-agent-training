import json
from typing import Any

from app.core.config import settings
from app.db.database import database_connected, init_db, session_scope
from app.db.models import (
    AgentSessionORM,
    AgentStepORM,
    DiagnosisRecordORM,
    FeedbackRecordORM,
    GeneratedResourceORM,
    LearnerProfileORM,
    LearningInteractionORM,
    LearningReportORM,
)


def db_enabled() -> bool:
    return settings.database_enabled or settings.data_backend.lower() == "sql"


def db_status() -> dict[str, Any]:
    enabled = db_enabled()
    return {
        "enabled": enabled,
        "data_backend": settings.data_backend,
        "connected": database_connected() if enabled else False,
    }


def seed_profiles(profiles: list[dict[str, Any]]) -> int:
    if not db_enabled():
        return 0
    init_db()
    count = 0
    with session_scope() as session:
        for profile in profiles:
            existing = (
                session.query(LearnerProfileORM)
                .filter(LearnerProfileORM.profile_id == profile["profile_id"])
                .one_or_none()
            )
            if existing is None:
                existing = LearnerProfileORM(profile_id=profile["profile_id"])
                session.add(existing)
            existing.name = profile["name"]
            existing.profile_type = profile["learner_type"]
            existing.background = profile["background"]
            existing.characteristics = profile.get("characteristics", "")
            existing.learning_goal = profile["default_goal"]
            existing.level = profile["self_level"]
            existing.recommended_domains = _json(profile.get("recommended_domains", []))
            count += 1
    return count


def list_profiles_from_db() -> list[dict[str, Any]]:
    if not db_enabled():
        return []
    try:
        init_db()
        with session_scope() as session:
            rows = session.query(LearnerProfileORM).order_by(LearnerProfileORM.id.asc()).all()
            return [
                {
                    "profile_id": row.profile_id,
                    "name": row.name,
                    "learner_type": row.profile_type,
                    "background": row.background,
                    "characteristics": row.characteristics,
                    "default_goal": row.learning_goal,
                    "self_level": row.level,
                    "recommended_domains": _loads(row.recommended_domains),
                }
                for row in rows
            ]
    except Exception:
        return []


def persist_agent_session(session_data: dict[str, Any]) -> bool:
    if not db_enabled():
        return False
    try:
        init_db()
        with session_scope() as session:
            _insert_agent_session(session, session_data)
            _insert_diagnosis(session, session_data)
            _insert_agent_steps(session, session_data)
            _insert_resources(session, session_data)
            _insert_report(session, session_data)
        return True
    except Exception:
        return False


def persist_feedback(session_id: str, feedback_response: Any, self_feedback: str) -> bool:
    if not db_enabled():
        return False
    try:
        init_db()
        with session_scope() as session:
            session.add(
                FeedbackRecordORM(
                    session_id=session_id,
                    feedback_score=feedback_response.feedback_score,
                    self_feedback=self_feedback,
                    next_action=feedback_response.next_action,
                    explanation=feedback_response.explanation,
                    updated_learning_path=_json(feedback_response.updated_learning_path),
                )
            )
        return True
    except Exception:
        return False


def list_feedback_records(session_id: str) -> list[dict[str, Any]]:
    if not db_enabled():
        return []
    try:
        init_db()
        with session_scope() as session:
            rows = (
                session.query(FeedbackRecordORM)
                .filter(FeedbackRecordORM.session_id == session_id)
                .order_by(FeedbackRecordORM.id.asc())
                .all()
            )
            return [_feedback_record_payload(row) for row in rows]
    except Exception:
        return []


def persist_learning_interaction(interaction: dict[str, Any]) -> bool:
    if not db_enabled():
        return False
    try:
        init_db()
        with session_scope() as session:
            session.add(
                LearningInteractionORM(
                    interaction_id=interaction["interaction_id"],
                    session_id=interaction["session_id"],
                    question=interaction["question"],
                    answer=interaction["answer"],
                    evidence_ids=_json(interaction.get("evidence_ids", [])),
                    retrieval_mode=interaction.get("retrieval_mode", ""),
                    knowledge_source=interaction.get("knowledge_source", ""),
                    generation_mode=interaction.get("generation_mode", ""),
                    review_status=interaction.get("review", {}).get("status", ""),
                    next_action=interaction.get("next_action", ""),
                    payload=_json(interaction),
                )
            )
        return True
    except Exception:
        return False


def list_learning_interactions(session_id: str) -> list[dict[str, Any]]:
    if not db_enabled():
        return []
    try:
        init_db()
        with session_scope() as session:
            rows = (
                session.query(LearningInteractionORM)
                .filter(LearningInteractionORM.session_id == session_id)
                .order_by(LearningInteractionORM.id.asc())
                .all()
            )
            return [_normalize_interaction_payload(_loads(row.payload)) for row in rows]
    except Exception:
        return []


def persist_report_snapshot(session_data: dict[str, Any]) -> bool:
    if not db_enabled():
        return False
    try:
        init_db()
        with session_scope() as session:
            _insert_report(session, session_data)
        return True
    except Exception:
        return False


def list_agent_sessions(limit: int = 30) -> list[dict[str, Any]]:
    if not db_enabled():
        return []
    try:
        init_db()
        with session_scope() as session:
            rows = (
                session.query(AgentSessionORM)
                .order_by(AgentSessionORM.updated_at.desc(), AgentSessionORM.id.desc())
                .limit(limit)
                .all()
            )
            summaries = []
            for row in rows:
                diagnosis = (
                    session.query(DiagnosisRecordORM)
                    .filter(DiagnosisRecordORM.session_id == row.session_id)
                    .order_by(DiagnosisRecordORM.id.desc())
                    .first()
                )
                interaction_count = (
                    session.query(LearningInteractionORM)
                    .filter(LearningInteractionORM.session_id == row.session_id)
                    .count()
                )
                summaries.append(
                    {
                        "session_id": row.session_id,
                        "profile_id": row.profile_id,
                        "domain": row.domain,
                        "learning_goal": row.learning_goal,
                        "status": row.status,
                        "diagnosis_score": diagnosis.score if diagnosis else None,
                        "diagnosis_level": diagnosis.level if diagnosis else "",
                        "weak_points": _loads(diagnosis.weak_points) if diagnosis else [],
                        "interaction_count": interaction_count,
                        "created_at": row.created_at.isoformat() if row.created_at else "",
                        "updated_at": row.updated_at.isoformat() if row.updated_at else "",
                    }
                )
            return summaries
    except Exception:
        return []


def persist_agent_iteration(session_data: dict[str, Any], steps: list[Any]) -> bool:
    if not db_enabled():
        return False
    try:
        init_db()
        with session_scope() as session:
            for step in steps:
                session.add(
                    AgentStepORM(
                        session_id=session_data["session_id"],
                        agent_name=step.agent_name,
                        role=step.role,
                        input_summary=step.input_summary,
                        output_summary=step.output_summary,
                        status=step.status,
                        confidence=step.confidence,
                        evidence_ids=_json(step.evidence_ids),
                        details=_json(step.details),
                    )
                )
            _insert_resources(session, session_data)
            _insert_report(session, session_data)
            agent_session = (
                session.query(AgentSessionORM)
                .filter(AgentSessionORM.session_id == session_data["session_id"])
                .one_or_none()
            )
            if agent_session:
                from datetime import datetime

                agent_session.updated_at = datetime.utcnow()
        return True
    except Exception:
        return False


def load_agent_session(session_id: str) -> dict[str, Any] | None:
    if not db_enabled():
        return None
    try:
        init_db()
        with session_scope() as session:
            session_row = (
                session.query(AgentSessionORM)
                .filter(AgentSessionORM.session_id == session_id)
                .one_or_none()
            )
            if session_row is None:
                return None
            diagnosis_row = (
                session.query(DiagnosisRecordORM)
                .filter(DiagnosisRecordORM.session_id == session_id)
                .order_by(DiagnosisRecordORM.id.desc())
                .first()
            )
            resource_row = (
                session.query(GeneratedResourceORM)
                .filter(GeneratedResourceORM.session_id == session_id)
                .order_by(GeneratedResourceORM.id.desc())
                .first()
            )
            step_rows = (
                session.query(AgentStepORM)
                .filter(AgentStepORM.session_id == session_id)
                .order_by(AgentStepORM.id.asc())
                .all()
            )
            feedback_rows = (
                session.query(FeedbackRecordORM)
                .filter(FeedbackRecordORM.session_id == session_id)
                .order_by(FeedbackRecordORM.id.asc())
                .all()
            )
            if diagnosis_row is None or resource_row is None or not step_rows:
                return None

            from app.models.schemas import AgentStep, DiagnosisResult
            from app.services.data_loader import get_knowledge_domain, get_profile

            steps = [
                AgentStep(
                    agent_name=row.agent_name,
                    role=row.role,
                    input_summary=row.input_summary,
                    output_summary=row.output_summary,
                    status=row.status,
                    confidence=row.confidence,
                    evidence_ids=_loads(row.evidence_ids),
                    details=_loads(row.details),
                )
                for row in step_rows
            ]
            diagnosis = DiagnosisResult(
                profile_id=diagnosis_row.profile_id,
                domain=diagnosis_row.domain,
                score=diagnosis_row.score,
                level=diagnosis_row.level,
                weak_points=_loads(diagnosis_row.weak_points),
                strong_points=_loads(diagnosis_row.strong_points),
                diagnosis_summary=diagnosis_row.diagnosis_summary,
                details=[],
            )
            profile = next(
                (
                    step.details.get("profile_snapshot")
                    for step in steps
                    if step.agent_name == "学情诊断 Agent"
                    and step.details.get("profile_snapshot")
                ),
                None,
            ) or get_profile(session_row.profile_id)
            resources = {
                "personalized_lecture": _loads(resource_row.personalized_lecture),
                "practical_guide": _loads(resource_row.practical_guide),
                "graded_quiz": _loads(resource_row.graded_quiz),
                "case_task": _loads(resource_row.case_task),
            }
            resources["difficulty_match"] = {
                "diagnosis_level": diagnosis.level,
                "resource_difficulty": resources["personalized_lecture"].get("difficulty", "巩固提升"),
                "reason": f"恢复自 SQL 会话；资源覆盖 {', '.join(diagnosis.weak_points)}。",
            }
            latest_retrieval = next(
                (step for step in reversed(steps) if "检索" in step.agent_name),
                None,
            )
            latest_review = next(
                (step for step in reversed(steps) if "审核" in step.agent_name),
                None,
            )
            latest_decision = next(
                (step for step in reversed(steps) if "决策" in step.agent_name),
                None,
            )
            return {
                "session_id": session_id,
                "profile": profile,
                "domain": session_row.domain,
                "domain_info": {
                    key: value
                    for key, value in get_knowledge_domain(session_row.domain).items()
                    if key in {"domain", "title", "summary"}
                },
                "diagnosis_result": diagnosis,
                "learning_goal": session_row.learning_goal,
                "retrieved_chunks": latest_retrieval.details.get("retrieved_chunks", []) if latest_retrieval else [],
                "retrieval_source": latest_retrieval.details.get("knowledge_source", "local-json") if latest_retrieval else "local-json",
                "retrieval_mode": latest_retrieval.details.get("retrieval_mode", "bm25") if latest_retrieval else "bm25",
                "resources": resources,
                "review": latest_review.details if latest_review else {},
                "decision": latest_decision.details if latest_decision else {},
                "agent_steps": steps[:6],
                "feedback_history": [_feedback_record_payload(row) for row in feedback_rows],
                "inquiry_history": list_learning_interactions(session_id),
            }
    except Exception:
        return None


def _insert_agent_session(session, session_data: dict[str, Any]) -> None:
    existing = (
        session.query(AgentSessionORM)
        .filter(AgentSessionORM.session_id == session_data["session_id"])
        .one_or_none()
    )
    if existing:
        return
    profile = session_data["profile"]
    session.add(
        AgentSessionORM(
            session_id=session_data["session_id"],
            profile_id=profile["profile_id"],
            domain=session_data["domain"],
            learning_goal=session_data["learning_goal"],
            status="completed",
        )
    )


def _insert_diagnosis(session, session_data: dict[str, Any]) -> None:
    diagnosis = session_data["diagnosis_result"]
    profile = session_data["profile"]
    session.add(
        DiagnosisRecordORM(
            session_id=session_data["session_id"],
            profile_id=profile["profile_id"],
            domain=session_data["domain"],
            score=diagnosis.score,
            level=diagnosis.level,
            weak_points=_json(diagnosis.weak_points),
            strong_points=_json(diagnosis.strong_points),
            diagnosis_summary=diagnosis.diagnosis_summary,
        )
    )


def _insert_agent_steps(session, session_data: dict[str, Any]) -> None:
    for step in session_data["agent_steps"]:
        session.add(
            AgentStepORM(
                session_id=session_data["session_id"],
                agent_name=step.agent_name,
                role=step.role,
                input_summary=step.input_summary,
                output_summary=step.output_summary,
                status=step.status,
                confidence=step.confidence,
                evidence_ids=_json(step.evidence_ids),
                details=_json(step.details),
            )
        )


def _insert_resources(session, session_data: dict[str, Any]) -> None:
    resources = session_data["resources"]
    session.add(
        GeneratedResourceORM(
            session_id=session_data["session_id"],
            personalized_lecture=_json(resources.get("personalized_lecture")),
            practical_guide=_json(resources.get("practical_guide")),
            graded_quiz=_json(resources.get("graded_quiz")),
            case_task=_json(resources.get("case_task")),
        )
    )


def _insert_report(session, session_data: dict[str, Any]) -> None:
    from app.services.report_service import build_export_markdown

    diagnosis = session_data["diagnosis_result"]
    decision = session_data["decision"]
    review = session_data["review"]
    session.add(
        LearningReportORM(
            session_id=session_data["session_id"],
            report_markdown=build_export_markdown(session_data),
            weak_points=_json(diagnosis.weak_points),
            learning_path=_json(decision.get("learning_path", [])),
            next_training_plan=decision.get("next_training_plan", ""),
            review_comments=_json(review),
        )
    )


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=_json_default)


def _json_default(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return str(value)


def _loads(value: str) -> Any:
    try:
        return json.loads(value)
    except Exception:
        return []


def _feedback_record_payload(row: FeedbackRecordORM) -> dict[str, Any]:
    return {
        "feedback_score": row.feedback_score,
        "self_feedback": row.self_feedback,
        "next_action": row.next_action,
        "explanation": row.explanation,
        "updated_learning_path": _loads(row.updated_learning_path),
        "created_at": row.created_at.isoformat() if row.created_at else "",
    }


def _normalize_interaction_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    payload.setdefault("generation_audit", {})
    payload["agent_steps"] = [
        step for step in payload.get("agent_steps", []) if isinstance(step, dict)
    ]
    return payload
