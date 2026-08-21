from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.database import reset_engine_cache
from app.main import app
from app.services.data_loader import load_demo_sessions
from app.services.session_store import session_store


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EVALUATION_DIR = PROJECT_ROOT / "evaluation"
RESULTS_PATH = EVALUATION_DIR / "fallback_acceptance_results.json"
SUMMARY_PATH = EVALUATION_DIR / "fallback_acceptance_summary.md"


def _require(response, label: str) -> Any:
    if response.status_code != 200:
        raise RuntimeError(f"{label} failed: HTTP {response.status_code} {response.text}")
    content_type = response.headers.get("content-type", "")
    return response.json() if "application/json" in content_type else response.text


def run_fallback_acceptance() -> dict[str, Any]:
    original = {
        "database_enabled": settings.database_enabled,
        "data_backend": settings.data_backend,
        "es_enabled": settings.es_enabled,
        "llm_enabled": settings.llm_enabled,
        "bge_enabled": settings.bge_enabled,
        "embedding_backend": settings.embedding_backend,
        "retrieval_mode": settings.retrieval_mode,
    }

    try:
        settings.database_enabled = False
        settings.data_backend = "json"
        settings.es_enabled = False
        settings.llm_enabled = False
        settings.bge_enabled = False
        settings.embedding_backend = "none"
        settings.retrieval_mode = "hybrid"
        reset_engine_cache()
        session_store.clear()

        client = TestClient(app)
        demo = load_demo_sessions()[0]

        health = _require(client.get("/api/health"), "health")
        if health["data_backend"] != "json":
            raise RuntimeError("Fallback health check did not report JSON data mode.")
        if health["database_enabled"] or health["es_enabled"] or health["llm_enabled"]:
            raise RuntimeError("Fallback health check still reports an external component enabled.")
        if health["knowledge_source"] != "local-json":
            raise RuntimeError("Fallback health check did not report local-json knowledge source.")

        profiles = _require(client.get("/api/profiles"), "profiles")
        domains = _require(client.get("/api/domains"), "domains")
        questions = _require(
            client.get("/api/questions", params={"domain": demo["domain"]}),
            "questions",
        )
        if len(profiles) < 3 or len(domains) < 3 or len(questions) < 5:
            raise RuntimeError("Fallback seed data is incomplete.")

        diagnosis = _require(
            client.post(
                "/api/diagnosis",
                json={
                    "profile_id": demo["profile_id"],
                    "domain": demo["domain"],
                    "answers": demo["diagnosis_answers"],
                },
            ),
            "diagnosis",
        )
        run = _require(
            client.post(
                "/api/agent/run",
                json={
                    "profile_id": demo["profile_id"],
                    "domain": demo["domain"],
                    "diagnosis_result": diagnosis,
                    "learning_goal": demo["learning_goal"],
                },
            ),
            "agent pipeline",
        )
        if len(run["agent_steps"]) != 6:
            raise RuntimeError("Fallback pipeline did not return six Agent steps.")

        retrieval_step = next(
            (
                step
                for step in run["agent_steps"]
                if "knowledge_source" in step.get("details", {})
            ),
            None,
        )
        if retrieval_step is None:
            raise RuntimeError("Fallback pipeline did not expose retrieval metadata.")
        if retrieval_step["details"]["knowledge_source"] != "local-json":
            raise RuntimeError("Fallback RetrievalAgent did not use local JSON.")

        session_id = run["session_id"]
        resources = _require(
            client.get(f"/api/sessions/{session_id}/resources"),
            "resources",
        )
        report = _require(
            client.get(f"/api/sessions/{session_id}/report"),
            "report",
        )
        export_markdown = _require(
            client.get(f"/api/sessions/{session_id}/export"),
            "report export",
        )
        feedback = _require(
            client.post(
                f"/api/sessions/{session_id}/feedback",
                json={
                    "answers": [],
                    "self_feedback": "希望使用更直观的胎面案例继续解释。",
                },
            ),
            "feedback",
        )

        resource_fields = {
            "personalized_lecture",
            "practical_guide",
            "graded_quiz",
            "case_task",
        }
        if not resource_fields.issubset(resources):
            raise RuntimeError("Fallback resources are missing one or more required forms.")
        if len(export_markdown) < 500:
            raise RuntimeError("Fallback report export is unexpectedly short.")
        if len(feedback.get("iteration_agent_steps", [])) != 4:
            raise RuntimeError("Fallback feedback did not run the four-step iteration pipeline.")

        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "passed",
            "mode": {
                "data_backend": "json",
                "database_enabled": False,
                "es_enabled": False,
                "llm_enabled": False,
                "knowledge_source": health["knowledge_source"],
                "effective_retrieval_mode": retrieval_step["details"].get(
                    "effective_retrieval_mode"
                ),
            },
            "flow": {
                "profile_count": len(profiles),
                "domain_count": len(domains),
                "question_count": len(questions),
                "diagnosis_score": diagnosis["score"],
                "diagnosis_level": diagnosis["level"],
                "agent_step_count": len(run["agent_steps"]),
                "agent_names": [step["agent_name"] for step in run["agent_steps"]],
                "evidence_count": len(retrieval_step.get("evidence_ids", [])),
                "resource_forms": sorted(resource_fields),
                "report_session_matches": report.get("session_id") == session_id,
                "export_character_count": len(export_markdown),
                "feedback_next_action": feedback["next_action"],
                "feedback_iteration_steps": len(feedback["iteration_agent_steps"]),
            },
            "checks": {
                "seed_data_loaded": True,
                "diagnosis_completed": True,
                "six_agent_pipeline_completed": True,
                "local_json_retrieval_used": True,
                "four_resource_forms_generated": True,
                "learning_report_generated": True,
                "markdown_export_generated": True,
                "feedback_iteration_completed": True,
            },
        }
        RESULTS_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        SUMMARY_PATH.write_text(_render_summary(payload), encoding="utf-8")
        return payload
    finally:
        for key, value in original.items():
            setattr(settings, key, value)
        reset_engine_cache()
        session_store.clear()


def _render_summary(payload: dict[str, Any]) -> str:
    flow = payload["flow"]
    mode = payload["mode"]
    rows = [
        "# JSON / mock 兜底模式全流程验收",
        "",
        f"运行时间：`{payload['generated_at']}`",
        "",
        "## 结论",
        "",
        "**通过。** 在 MySQL、Elasticsearch、LLM 和 BGE 均关闭的情况下，系统仍完成完整训练闭环。",
        "",
        "| 检查项 | 结果 |",
        "| --- | --- |",
        f"| 数据模式 | {mode['data_backend']} |",
        f"| 知识来源 | {mode['knowledge_source']} |",
        f"| 有效检索模式 | {mode['effective_retrieval_mode']} |",
        f"| 学习者画像 | {flow['profile_count']} 组 |",
        f"| 材料方向 | {flow['domain_count']} 类 |",
        f"| 诊断题 | {flow['question_count']} 道 |",
        f"| Agent 步骤 | {flow['agent_step_count']} 步 |",
        f"| 检索证据 | {flow['evidence_count']} 条 |",
        f"| 个性化资源 | {len(flow['resource_forms'])} 类 |",
        f"| 导出报告字符数 | {flow['export_character_count']} |",
        f"| 反馈迭代 | {flow['feedback_iteration_steps']} 个 Agent，动作：{flow['feedback_next_action']} |",
        "",
        "> 本验收在 FastAPI 进程内临时切换配置，不会停止 Docker 容器，也不会向 MySQL 写入测试记录。",
    ]
    return "\n".join(rows) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the complete JSON/mock fallback API flow.")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    payload = run_fallback_acceptance()
    output = {
        "status": payload["status"],
        "knowledge_source": payload["mode"]["knowledge_source"],
        "agent_step_count": payload["flow"]["agent_step_count"],
        "resource_form_count": len(payload["flow"]["resource_forms"]),
        "feedback_iteration_steps": payload["flow"]["feedback_iteration_steps"],
        "results": str(RESULTS_PATH.relative_to(PROJECT_ROOT)),
    }
    print(json.dumps(output if args.quiet else payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
