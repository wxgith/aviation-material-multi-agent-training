from app.agents.base_agent import BaseAgent
from app.evidence.catalog import condition_match_strategy, parse_condition_query, resolve_assets
from app.models.schemas import AgentStep
from app.search.retriever import retrieve_with_rag_metadata


class RetrievalAgent(BaseAgent):
    agent_name = "专业知识检索 Agent"
    role = "根据薄弱点、学习目标和学习者类型，从 Elasticsearch 或 JSON fallback 检索证据片段。"

    def run(self, context: dict) -> AgentStep:
        profile = context["profile"]
        retrieval = retrieve_with_rag_metadata(
            domain=context["domain"],
            weak_points=context["weak_points"],
            learning_goal="；".join(
                item for item in [
                    context["learning_goal"],
                    context.get("feedback_explanation", ""),
                    context.get("self_feedback", ""),
                ] if item
            ),
            learner_type=profile["learner_type"],
            top_k=5,
        )
        chunks = retrieval["chunks"]
        retrieval_source = retrieval["knowledge_source"]
        context["retrieved_chunks"] = chunks
        context["retrieval_source"] = retrieval_source
        context["retrieval_mode"] = retrieval["retrieval_mode"]
        evidence_ids = [chunk["id"] for chunk in chunks]
        source_ids = list(
            dict.fromkeys(chunk.get("source_id", "") for chunk in chunks if chunk.get("source_id"))
        )
        asset_query_text = " ".join(
            context["weak_points"]
            + [
                context["learning_goal"],
                context.get("feedback_explanation", ""),
                context.get("self_feedback", ""),
            ]
        )
        condition_query = parse_condition_query(asset_query_text)
        experimental_evidence = resolve_assets(
            evidence_ids=evidence_ids,
            source_ids=source_ids,
            limit=8,
            query_text=asset_query_text,
        )
        context["experimental_evidence"] = experimental_evidence

        return self.step(
            input_summary=f"薄弱点：{', '.join(context['weak_points'])}；目标：{context['learning_goal']}",
            output_summary=(
                f"检索到 {len(chunks)} 条相关知识片段，"
                f"模式：{retrieval['retrieval_mode']}，来源：{retrieval_source}。"
            ),
            confidence=0.88,
            evidence_ids=evidence_ids,
            details={
                "retrieval_mode": retrieval["retrieval_mode"],
                "effective_retrieval_mode": retrieval["effective_retrieval_mode"],
                "knowledge_source": retrieval_source,
                "retrieval_source": retrieval_source,
                "evidence_ids": retrieval["evidence_ids"],
                "evidence_titles": retrieval["evidence_titles"],
                "retrieval_scores": retrieval["retrieval_scores"],
                "evidence_source_ids": source_ids,
                "experimental_evidence": experimental_evidence,
                "condition_constraints": condition_query,
                "condition_match_strategy": condition_match_strategy(condition_query),
                "embedding": retrieval["embedding"],
                "vector_note": retrieval["vector_note"],
                "retrieved_chunks": chunks,
            },
        )
