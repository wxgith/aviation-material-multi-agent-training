import json

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse, StreamingResponse

from app.agents.orchestrator import orchestrator
from app.agents.inquiry_orchestrator import guided_inquiry_orchestrator
from app.core.config import settings
from app.db.repositories import (
    db_status,
    list_agent_sessions,
    list_learning_interactions,
    list_profiles_from_db,
    load_agent_session,
)
from app.db.task_repository import task_persistence_status
from app.evidence.catalog import (
    catalog_status,
    get_asset,
    list_assets,
    media_path,
    resolve_assets,
)
from app.models.schemas import (
    AgentRunRequest,
    AgentRunResponse,
    DiagnosisSubmitRequest,
    FeedbackRequest,
    GuidedInquiryRequest,
    GuidedInquiryResponse,
    InterfaceAssistantRequest,
    InterfaceAssistantResponse,
    LegacyDiagnosticRequest,
    TrainingDomain,
)
from app.services.data_loader import (
    get_data_status,
    get_domains,
    get_profile,
    get_questions_by_domain,
    load_demo_sessions,
    load_profiles,
)
from app.services.diagnosis_service import evaluate_diagnosis
from app.services.corpus_service import build_source_catalog
from app.services.literature_evidence_service import list_literature_experiments
from app.services.evaluation_service import get_evaluation_summary
from app.services.report_service import build_export_markdown, build_report, evaluate_feedback
from app.search.es_client import es_connected
from app.rag.team_dataset_validator import DEFAULT_DATASET_ROOT, validate_team_dataset
from app.services.session_store import session_store
from app.services.task_manager import TERMINAL_STATUSES, task_manager
from app.services.assistant_service import run_interface_assistant

router = APIRouter()


def _get_session(session_id: str) -> dict:
    try:
        return session_store.get(session_id)
    except KeyError:
        recovered = load_agent_session(session_id)
        if recovered is None:
            raise
        return session_store.put(recovered)


def _agent_runner_from_payload(payload: dict):
    request = AgentRunRequest.model_validate(payload)

    def runner(emit, cancelled):
        session = orchestrator.run(
            request,
            progress_callback=emit,
            cancel_check=cancelled,
        )
        return {
            "session_id": session["session_id"],
            "agent_steps": session["agent_steps"],
        }

    return runner


def _guided_runner_from_payload(payload: dict):
    session_id = payload["session_id"]
    request = GuidedInquiryRequest.model_validate(payload["request"])

    def runner(emit, cancelled):
        return guided_inquiry_orchestrator.run(
            _get_session(session_id),
            request.question.strip(),
            progress_callback=emit,
            cancel_check=cancelled,
        )

    return runner


def _assistant_runner_from_payload(payload: dict):
    request = InterfaceAssistantRequest.model_validate(payload)

    def runner(emit, cancelled):
        session = None
        if request.context.session_id:
            try:
                session = _get_session(request.context.session_id)
            except KeyError:
                session = None
        return run_interface_assistant(
            request,
            session=session,
            progress_callback=emit,
            cancel_check=cancelled,
        )

    return runner


task_manager.register_runner_factory("agent_run", _agent_runner_from_payload)
task_manager.register_runner_factory("guided_inquiry", _guided_runner_from_payload)
task_manager.register_runner_factory("interface_assistant", _assistant_runner_from_payload)


@router.get("/health")
def health() -> dict:
    data_status = get_data_status()
    database_status = db_status()
    es_is_connected = es_connected()
    team_dataset = validate_team_dataset(DEFAULT_DATASET_ROOT)
    llm_configured = bool(settings.llm_enabled and settings.llm_base_url and settings.llm_model)
    task_store = task_persistence_status()
    return {
        "status": "ok",
        "backend_status": "ok",
        "version": settings.version,
        "data_backend": settings.data_backend,
        "database_enabled": database_status["enabled"],
        "database_connected": database_status["connected"],
        "es_enabled": settings.es_enabled,
        "es_connected": es_is_connected,
        "es_url": settings.es_url,
        "es_index": settings.es_index_knowledge,
        "retrieval_mode": settings.retrieval_mode,
        "bge_enabled": settings.bge_enabled,
        "embedding_backend": settings.embedding_backend,
        "llm_enabled": settings.llm_enabled,
        "llm_resource_generation_enabled": settings.llm_resource_generation_enabled,
        "llm_semantic_review_enabled": settings.llm_semantic_review_enabled,
        "llm_configured": llm_configured,
        "llm_model": settings.llm_model,
        "knowledge_source": "elasticsearch" if settings.es_enabled and es_is_connected else "local-json",
        "llm": {
            "enabled": settings.llm_enabled,
            "mode": (
                "llm-ready"
                if llm_configured
                else ("llm-misconfigured" if settings.llm_enabled else "mock-template")
            ),
            "model": settings.llm_model,
            "configured": llm_configured,
            "base_url_configured": bool(settings.llm_base_url),
            "guided_inquiry_available": True,
            "interface_assistant_available": True,
            "resource_generation_enabled": settings.llm_resource_generation_enabled,
            "semantic_review_enabled": settings.llm_semantic_review_enabled,
            "fallback_enabled": True,
        },
        "data": data_status,
        "team_dataset": {
            "status": team_dataset["status"],
            "mode": team_dataset["mode"],
            "approved_for_rag": team_dataset["approved_for_rag"],
            "image_files": team_dataset["image_files"],
        },
        "experimental_evidence": catalog_status(),
        "async_tasks": {
            "persistence_enabled": task_store["enabled"],
            "persistence_connected": task_store["connected"],
            "table_ready": task_store["table_ready"],
            "restart_policy": "recover-completed-and-retry-interrupted",
            "interrupted_on_startup": task_manager.last_recovery_count,
        },
    }


@router.get("/profiles")
def profiles() -> list[dict]:
    sql_profiles = list_profiles_from_db()
    return sql_profiles or load_profiles()


@router.get("/learners")
def learners() -> list[dict]:
    sql_profiles = list_profiles_from_db()
    return sql_profiles or load_profiles()


@router.get("/domains")
def domains() -> list[dict]:
    return get_domains()


@router.get("/questions")
def questions(domain: TrainingDomain = Query(...)) -> list[dict]:
    return get_questions_by_domain(domain)


@router.get("/domains/{domain}/questions")
def diagnostic_questions(domain: TrainingDomain) -> list[dict]:
    return get_questions_by_domain(domain)


@router.get("/demo-sessions")
def demo_sessions() -> list[dict]:
    return load_demo_sessions()


@router.get("/knowledge/sources")
def knowledge_sources(
    domain: str | None = Query(default=None),
    query: str | None = Query(default=None, max_length=120),
) -> dict:
    return build_source_catalog(domain=domain, query=query)


@router.get("/knowledge/experiments")
def knowledge_experiments(domain: str | None = Query(default=None)) -> dict:
    return list_literature_experiments(domain=domain)


@router.get("/evaluation/summary")
def evaluation_summary() -> dict:
    return get_evaluation_summary()


@router.get("/evidence/assets")
def evidence_assets(
    evidence_ids: list[str] = Query(default=[]),
    source_ids: list[str] = Query(default=[]),
    topic: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    assets = (
        resolve_assets(evidence_ids, source_ids, limit=limit)
        if evidence_ids or source_ids
        else list_assets(topic=topic, limit=limit)
    )
    return {"count": len(assets), "assets": assets}


@router.get("/evidence/assets/{asset_id}/media")
def evidence_asset_media(asset_id: str):
    path = media_path(asset_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Experimental evidence media not found")
    asset = get_asset(asset_id) or {}
    return FileResponse(
        path,
        media_type=asset.get("media_type", "application/octet-stream"),
        filename=path.name,
    )


@router.get("/evidence/assets/{asset_id}")
def evidence_asset(asset_id: str) -> dict:
    asset = get_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Experimental evidence asset not found")
    return asset


@router.post("/diagnosis")
def submit_diagnosis(request: DiagnosisSubmitRequest):
    try:
        profile_override = (
            request.profile_override.model_dump()
            if request.profile_override is not None
            else None
        )
        return evaluate_diagnosis(
            request.profile_id,
            request.domain,
            request.answers,
            profile_override=profile_override,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/agent/run", response_model=AgentRunResponse)
def run_agents(request: AgentRunRequest):
    try:
        session = orchestrator.run(request)
        return {
            "session_id": session["session_id"],
            "agent_steps": session["agent_steps"],
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/agent/tasks")
def start_agent_task(request: AgentRunRequest) -> dict:
    payload = request.model_dump(mode="json")
    return task_manager.create(
        "agent_run",
        _agent_runner_from_payload(payload),
        metadata={"profile_id": request.profile_id, "domain": request.domain},
        request_payload=payload,
    )


@router.get("/tasks/{task_id}")
def task_status(task_id: str) -> dict:
    try:
        return task_manager.snapshot(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/tasks/{task_id}/events")
def task_events(task_id: str, cursor: int = Query(default=0, ge=0)):
    try:
        task_manager.snapshot(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    def stream():
        next_cursor = cursor
        while True:
            events, status = task_manager.events_since(task_id, next_cursor, timeout=8)
            if not events:
                yield ": keepalive\n\n"
            for event in events:
                next_cursor = event["event_id"] + 1
                payload = json.dumps(event, ensure_ascii=False)
                yield f"id: {event['event_id']}\nevent: progress\ndata: {payload}\n\n"
            if status in TERMINAL_STATUSES:
                break

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/tasks/{task_id}/cancel")
def cancel_task(task_id: str) -> dict:
    try:
        return task_manager.cancel(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/retry")
def retry_task(task_id: str) -> dict:
    try:
        return task_manager.retry(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/sessions")
def sessions(limit: int = Query(default=30, ge=1, le=100)) -> dict:
    items = list_agent_sessions(limit=limit) or session_store.list_summaries(limit=limit)
    return {"count": len(items), "items": items}


@router.get("/sessions/{session_id}")
def session_snapshot(session_id: str) -> dict:
    try:
        session = _get_session(session_id)
        return {
            "session_id": session_id,
            "profile": session["profile"],
            "domain": session["domain"],
            "learning_goal": session["learning_goal"],
            "diagnosis_result": session["diagnosis_result"],
            "agent_steps": session["agent_steps"],
            "resources": session["resources"],
            "report": build_report(session),
            "inquiry_history": session.get("inquiry_history", [])
            or list_learning_interactions(session_id),
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/sessions/{session_id}/resources")
def session_resources(session_id: str) -> dict:
    try:
        return _get_session(session_id)["resources"]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/sessions/{session_id}/report")
def session_report(session_id: str) -> dict:
    try:
        return build_report(_get_session(session_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/sessions/{session_id}/export")
def session_export(session_id: str):
    try:
        markdown = build_export_markdown(_get_session(session_id))
        filename = f"learning-report-{session_id}.md"
        return Response(
            content=markdown,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/feedback")
def session_feedback(session_id: str, request: FeedbackRequest):
    try:
        session = _get_session(session_id)
        return evaluate_feedback(session, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/sessions/{session_id}/ask",
    response_model=GuidedInquiryResponse,
)
def guided_inquiry(session_id: str, request: GuidedInquiryRequest):
    try:
        session = _get_session(session_id)
        return guided_inquiry_orchestrator.run(session, request.question.strip())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/inquiry-tasks")
def start_guided_inquiry_task(session_id: str, request: GuidedInquiryRequest) -> dict:
    try:
        session = _get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    question = request.question.strip()
    payload = {"session_id": session_id, "request": request.model_dump(mode="json")}

    return task_manager.create(
        "guided_inquiry",
        _guided_runner_from_payload(payload),
        metadata={"session_id": session_id, "question": question},
        request_payload=payload,
    )


@router.get("/sessions/{session_id}/inquiries")
def guided_inquiry_history(session_id: str) -> dict:
    try:
        session = _get_session(session_id)
        history = session.get("inquiry_history", []) or list_learning_interactions(session_id)
        return {"session_id": session_id, "count": len(history), "items": history}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/assistant/ask", response_model=InterfaceAssistantResponse)
def interface_assistant(request: InterfaceAssistantRequest):
    session = None
    if request.context.session_id:
        try:
            session = _get_session(request.context.session_id)
        except KeyError:
            session = None
    return run_interface_assistant(request, session=session)


@router.post("/assistant/tasks")
def start_interface_assistant_task(request: InterfaceAssistantRequest) -> dict:
    payload = request.model_dump(mode="json")
    return task_manager.create(
        "interface_assistant",
        _assistant_runner_from_payload(payload),
        metadata={
            "session_id": request.context.session_id,
            "active_view": request.context.active_view,
            "question": request.question.strip(),
        },
        request_payload=payload,
    )


@router.post("/orchestrate")
def legacy_orchestrate(request: LegacyDiagnosticRequest):
    profile_id = request.profile.get("profile_id") or request.profile.get("learner_id") or "undergrad_basic"
    domain = request.profile.get("domain") or "tire"
    if profile_id not in {item["profile_id"] for item in load_profiles()}:
        profile_id = "undergrad_basic"
    profile = get_profile(profile_id)
    diagnosis = evaluate_diagnosis(profile_id, domain, request.answers)
    session = orchestrator.run(
        AgentRunRequest(
            profile_id=profile_id,
            domain=domain,
            diagnosis_result=diagnosis,
            learning_goal=request.profile.get("goal") or profile["default_goal"],
        )
    )
    return {
        "session_id": session["session_id"],
        "profile": profile,
        "score": diagnosis.score,
        "weak_points": diagnosis.weak_points,
        "agent_steps": session["agent_steps"],
        "resources": session["resources"],
        "review": session["review"],
        "decision": session["decision"],
    }
