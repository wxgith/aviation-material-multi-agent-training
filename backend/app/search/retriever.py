from __future__ import annotations

from app.core.config import settings
from app.evidence.catalog import parse_condition_query
from app.rag.embedder import cosine_similarity, embed_texts, embedding_status
from app.search.es_client import es_connected, get_es_client
from app.services.data_loader import get_knowledge_domain
from app.services.retrieval_service import retrieve_knowledge


SUPPORTED_RETRIEVAL_MODES = {"bm25", "vector", "hybrid"}

DOMAIN_QUERY_EXPANSIONS = {
    "热氧老化": "thermo-oxidative aging thermal oxidation aging",
    "滑动磨损": "sliding wear abrasion fatigue wear",
    "磨损形貌": "wear morphology worn surface",
    "胎面裂纹": "tread crack cracking",
    "轮胎欠压": "tire underinflation underinflated tire pressure",
    "跑道工况": "runway surface asphalt concrete slip ratio",
    "事故案例": "accident probable cause failure chain rejected takeoff",
    "高温摩擦": "high-temperature friction frictional heating",
    "热衰退": "thermal fade friction fade",
    "维护决策": "maintenance decision predictive maintenance wear pin",
    "刹车检查": "brake inspection brake lining brake disk brake assembly",
    "刹车衬片": "brake lining wear indicator wear pin minimum thickness",
    "刹车放气": "brake bleeding hydraulic fluid pressure bleeding trapped air",
    "刹车过热": "brake overheat rejected takeoff inspection heat damage",
    "冲击损伤": "impact damage low velocity impact",
    "分层": "delamination disbond",
    "基体开裂": "matrix cracking transverse crack",
    "纤维断裂": "fiber breakage fiber failure",
    "无损检测": "nondestructive testing ultrasonic C-scan X-ray CT",
    "敲击检测": "coin tap audible sonic testing delamination disbond",
    "超声检测": "ultrasonic inspection pulse echo through transmission bond tester",
    "无损检测图像判读": "ultrasonic C-scan image interpretation X-ray CT",
    "剪切散斑检测": "shearography nondestructive evaluation",
    "冲击后剩余强度": "compression after impact residual strength",
    "往复摩擦": "reciprocating friction load distance cylinder flat",
    "滑动距离": "sliding distance wear loss hardness",
    "载荷": "normal load contact pressure",
    "交联密度": "crosslink density thermal aging natural rubber carbon black",
    "撕裂能": "tearing energy pure shear fatigue crack propagation",
    "疲劳裂纹扩展": "fatigue crack growth filled natural rubber",
    "碳石墨": "carbon graphite high energy brake",
    "剪切膜": "graphite shear film disruption severe wear",
    "表面深度云图": "surface depth contour impact condition C-scan",
    "可见冲击损伤": "barely visible impact damage BVID reconstruction",
}


def retrieve_with_optional_es(
    domain: str,
    weak_points: list[str],
    learning_goal: str,
    learner_type: str,
    top_k: int = 5,
) -> tuple[list[dict], str]:
    result = retrieve_with_rag_metadata(domain, weak_points, learning_goal, learner_type, top_k)
    return result["chunks"], result["knowledge_source"]


def retrieve_with_rag_metadata(
    domain: str,
    weak_points: list[str],
    learning_goal: str,
    learner_type: str,
    top_k: int = 5,
) -> dict:
    mode = _retrieval_mode()
    bm25_chunks: list[dict] = []
    bm25_source = "local-json"
    bm25_error = ""

    if mode in {"bm25", "hybrid"}:
        bm25_chunks, bm25_source, bm25_error = _bm25_or_fallback(
            domain, weak_points, learning_goal, learner_type, top_k
        )

    vector_chunks: list[dict] = []
    vector_note = "vector disabled"
    if mode in {"vector", "hybrid"}:
        vector_chunks, vector_note = _retrieve_with_local_vector(
            domain, weak_points, learning_goal, learner_type, top_k
        )

    if mode == "vector":
        if vector_chunks:
            chunks = vector_chunks[:top_k]
            source = "json-vector"
            effective_mode = "vector"
        else:
            chunks, source, bm25_error = _bm25_or_fallback(domain, weak_points, learning_goal, learner_type, top_k)
            effective_mode = "bm25-fallback"
            vector_note = f"{vector_note}; fallback to BM25"
    elif mode == "hybrid":
        if vector_chunks:
            chunks = _merge_ranked_results(bm25_chunks, vector_chunks, top_k)
            source = bm25_source if bm25_chunks else "json-vector"
            effective_mode = "hybrid"
        else:
            chunks = bm25_chunks
            source = bm25_source
            effective_mode = "hybrid-bm25-only"
    else:
        chunks = bm25_chunks
        source = bm25_source
        effective_mode = "bm25"

    return {
        "chunks": chunks,
        "knowledge_source": source,
        "retrieval_mode": mode,
        "effective_retrieval_mode": effective_mode,
        "evidence_ids": [chunk.get("id", "") for chunk in chunks],
        "evidence_titles": [chunk.get("title", "") for chunk in chunks],
        "retrieval_scores": [
            round(float(chunk.get("_combined_score", chunk.get("_score", 0.0))), 4) for chunk in chunks
        ],
        "embedding": embedding_status(),
        "vector_note": vector_note,
        "bm25_error": bm25_error,
    }


def _retrieval_mode() -> str:
    mode = (settings.retrieval_mode or "hybrid").lower().strip()
    return mode if mode in SUPPORTED_RETRIEVAL_MODES else "hybrid"


def _bm25_or_fallback(
    domain: str,
    weak_points: list[str],
    learning_goal: str,
    learner_type: str,
    top_k: int,
) -> tuple[list[dict], str, str]:
    if settings.es_enabled and es_connected():
        try:
            results = _retrieve_from_es(domain, weak_points, learning_goal, learner_type, top_k)
            if results:
                return _with_rank_scores(results, "elasticsearch"), "elasticsearch", ""
        except Exception as exc:
            local = retrieve_knowledge(domain, weak_points, learning_goal, learner_type, top_k)
            return _with_rank_scores(local, "local-json-fallback"), "local-json-fallback", str(exc)

    local = retrieve_knowledge(domain, weak_points, learning_goal, learner_type, top_k)
    source = "local-json-fallback" if settings.es_enabled else "local-json"
    return _with_rank_scores(local, source), source, ""


def _retrieve_from_es(
    domain: str,
    weak_points: list[str],
    learning_goal: str,
    learner_type: str,
    top_k: int,
) -> list[dict]:
    client = get_es_client()
    query_text = _expand_query_terms(weak_points, learning_goal, learner_type)
    preferred_sources = _preferred_source_ids(" ".join(weak_points + [learning_goal]))
    should_queries = [
        {
            "multi_match": {
                "query": query_text,
                "fields": ["title^3", "tags^5", "content", "common_misconceptions"],
            }
        },
        {"terms": {"tags": weak_points, "boost": 12}},
        {"term": {"applicable_learners": learner_type}},
        {"term": {"source_authority": {"value": "official_primary", "boost": 4}}},
    ]
    if preferred_sources:
        # An explicit experiment condition in the learning goal should outrank
        # broad diagnostic terms while still allowing supporting evidence.
        should_queries.extend(
            {
                "term": {
                    "source_id": {
                        "value": source_id,
                        "boost": _preferred_source_boost(index),
                    }
                }
            }
            for index, source_id in enumerate(preferred_sources)
        )
    response = client.search(
        index=settings.es_index_knowledge,
        # Source-level boosts can place many chunks from one long report first.
        # Fetch a wider candidate pool so the diversity pass can still retain
        # complementary manuals, local foundations and experiment records.
        size=max(top_k * 24, 120),
        query={
            "bool": {
                "filter": [{"term": {"domain": domain}}],
                "should": should_queries,
                "minimum_should_match": 1,
            }
        },
    )
    chunks = []
    for hit in response["hits"]["hits"]:
        source = dict(hit["_source"])
        source["_score"] = hit.get("_score", 0)
        source["_retrieval_source"] = "elasticsearch"
        chunks.append(source)
    condition_query = parse_condition_query(" ".join(weak_points + [learning_goal]))
    chunks = _rerank_experimental_conditions(chunks, condition_query)
    max_per_source = (
        2
        if len(preferred_sources) >= 3
        else 3 if condition_query.get("target_topic") else 2
    )
    diversified = _diversify_by_source(chunks, top_k, max_per_source=max_per_source)
    selected = _ensure_authoritative_evidence(diversified, weak_points, top_k)
    return _ensure_core_knowledge_anchors(
        selected=selected,
        domain=domain,
        weak_points=weak_points,
        learning_goal=learning_goal,
        learner_type=learner_type,
        top_k=top_k,
        condition_query=condition_query,
    )


def _preferred_source_ids(query_text: str) -> list[str]:
    compact = query_text.lower().replace(" ", "")
    preferred: list[str] = []
    load_matrix_signals = (
        "往复摩擦",
        "载荷-距离",
        "载荷与距离",
        "磨损量",
        "硬度",
        "60n",
        "160m",
    )
    if any(signal in compact for signal in load_matrix_signals):
        preferred.extend(
            [
                "team_tire_lyq_load_distance_matrix",
                "team_tire_lyq_contact_load_temperature_evidence",
            ]
        )
    if "紫外" in compact or any(marker in compact for marker in ("24h", "504h", "576h")):
        preferred.extend(
            [
                "team_tire_rxq_uv_wear_morphology",
                "team_tire_rxq_aging_multimodal_evidence",
            ]
        )
    if "热氧老化" in compact and any(signal in compact for signal in ("对照", "表征", "主导")):
        preferred.extend(
            [
                "team_tire_rxq_aging_multimodal_evidence",
                "team_tire_tire_exp_rxq_aging_001",
            ]
        )
    source_signals = [
        (
            ("交联密度", "天然橡胶炭黑", "热老化后拉伸"),
            "tire_pmc_10490132_thermal_aging",
        ),
        (
            ("撕裂能", "疲劳裂纹扩展", "fatiguecrackpropagation", "pureshear"),
            "tire_pmc_8620932_fatigue_crack",
        ),
        (
            ("碳石墨", "剪切膜", "carbon-graphite", "graphiteshearfilm"),
            "brake_nasa_tn_d_8006",
        ),
        (
            ("bvid", "可见冲击损伤", "多层分层重构"),
            "composite_pmc_6865209_bvid_reconstruction",
        ),
        (
            ("表面深度云图", "表面与内部损伤", "surfaceandinternaldamage"),
            "composite_pmc_9294053_impact_dataset",
        ),
        (
            ("敲击检测", "敲击法", "cointap", "audiblesonic", "复材维修检查"),
            "composite_faa_h_8083_31b_ch7_ndi",
        ),
        (
            ("刹车衬片", "刹车放气", "刹车过热", "brakelining", "brakebleeding"),
            "brake_faa_h_8083_31b_ch13_service",
        ),
    ]
    for signals, source_id in source_signals:
        if any(signal in compact for signal in signals):
            preferred.append(source_id)
    return list(dict.fromkeys(preferred))


def _preferred_source_boost(index: int) -> int:
    return max(20, 260 - index * 60)


def _expand_query_terms(
    weak_points: list[str], learning_goal: str, learner_type: str
) -> str:
    original_terms = weak_points + [learning_goal, learner_type]
    source = " ".join(original_terms)
    expansions = [
        english
        for chinese, english in DOMAIN_QUERY_EXPANSIONS.items()
        if chinese in source
    ]
    return " ".join(original_terms + expansions)


def _ensure_authoritative_evidence(
    chunks: list[dict], weak_points: list[str], top_k: int
) -> list[dict]:
    selected = chunks[:top_k]
    traceable_authorities = {
        "official_primary",
        "peer_reviewed_open_access",
        "peer_reviewed_open_dataset",
        "open_dataset",
        "team_authorized_experiment",
    }
    if any(chunk.get("source_authority") in traceable_authorities for chunk in selected):
        return selected
    weak_set = set(weak_points)
    authoritative = next(
        (
            chunk
            for chunk in chunks
            if chunk.get("source_authority") in traceable_authorities
            and weak_set.intersection(chunk.get("tags", []))
        ),
        None,
    )
    if authoritative is None:
        authoritative = next(
            (
                chunk
                for chunk in chunks
                if chunk.get("source_authority") in traceable_authorities
            ),
            None,
        )
    if authoritative is None:
        return selected
    if len(selected) < top_k:
        return selected + [authoritative]
    return selected[:-1] + [authoritative]


def _ensure_core_knowledge_anchors(
    selected: list[dict],
    domain: str,
    weak_points: list[str],
    learning_goal: str,
    learner_type: str,
    top_k: int,
    condition_query: dict,
) -> list[dict]:
    """Keep foundational teaching anchors beside long-form experimental evidence."""
    if condition_query.get("target_topic"):
        return selected[:top_k]
    anchors = retrieve_knowledge(
        domain=domain,
        weak_points=weak_points,
        learning_goal=learning_goal,
        learner_type=learner_type,
        top_k=min(3, top_k),
    )
    result = list(selected[:top_k])
    existing_ids = {chunk.get("id") for chunk in result}
    replacement_index = len(result) - 1
    for anchor in anchors:
        if anchor.get("id") in existing_ids:
            continue
        enriched = dict(anchor)
        enriched.setdefault("_score", 0.0)
        enriched["_retrieval_source"] = "local-json-anchor"
        if len(result) < top_k:
            result.append(enriched)
        elif replacement_index >= 1:
            existing_ids.discard(result[replacement_index].get("id"))
            result[replacement_index] = enriched
            replacement_index -= 1
        existing_ids.add(enriched.get("id"))
    return result


def _diversify_by_source(
    chunks: list[dict], top_k: int, max_per_source: int = 2
) -> list[dict]:
    """Preserve rank while preventing one document from filling all evidence slots."""
    selected: list[dict] = []
    deferred: list[dict] = []
    source_counts: dict[str, int] = {}
    for chunk in chunks:
        source_id = chunk.get("source_id") or chunk.get("id", "unknown")
        if source_counts.get(source_id, 0) < max_per_source:
            selected.append(chunk)
            source_counts[source_id] = source_counts.get(source_id, 0) + 1
        else:
            deferred.append(chunk)
        if len(selected) >= top_k:
            return selected
    for chunk in deferred:
        selected.append(chunk)
        if len(selected) >= top_k:
            break
    return selected


def _rerank_experimental_conditions(
    chunks: list[dict], condition_query: dict
) -> list[dict]:
    target_topic = condition_query.get("target_topic")
    if not target_topic:
        return chunks
    preferred_sources = {
        "load_distance_morphology_matrix": {
            "team_tire_lyq_load_distance_matrix",
            "team_tire_lyq_contact_load_temperature_evidence",
        },
        "uv_aging_wear_morphology": {
            "team_tire_rxq_uv_wear_morphology",
            "team_tire_rxq_aging_multimodal_evidence",
        },
    }[target_topic]

    def condition_score(chunk: dict) -> float:
        searchable = f"{chunk.get('title', '')} {chunk.get('content', '')}".lower().replace(" ", "")
        score = 100.0 if chunk.get("source_id") in preferred_sources else 0.0
        for value in condition_query.get("normal_load_N", []):
            score += 12.0 if f"{value:g}n" in searchable else 0.0
        for value in condition_query.get("sliding_distance_m", []):
            score += 12.0 if f"{value:g}m" in searchable else 0.0
        for value in condition_query.get("aging_duration_h", []):
            score += 12.0 if f"{value:g}h" in searchable else 0.0
        return score

    ranked = sorted(
        enumerate(chunks),
        key=lambda item: (-condition_score(item[1]), item[0]),
    )
    return [
        chunk
        for _, chunk in ranked
    ]


def _retrieve_with_local_vector(
    domain: str,
    weak_points: list[str],
    learning_goal: str,
    learner_type: str,
    top_k: int,
) -> tuple[list[dict], str]:
    query = " ".join(weak_points + [learning_goal, learner_type])
    knowledge = get_knowledge_domain(domain)
    chunks = knowledge.get("chunks", [])
    texts = [query] + [f"{chunk.get('title', '')}\n{chunk.get('content', '')}" for chunk in chunks]
    vectors = embed_texts(texts)
    if vectors is None:
        return [], "embedding unavailable; BM25 remains active"
    query_vector = vectors[0]
    ranked = []
    for chunk, vector in zip(chunks, vectors[1:]):
        enriched = dict(chunk)
        score = cosine_similarity(query_vector, vector)
        enriched["_score"] = score
        enriched["_vector_score"] = score
        enriched["_retrieval_source"] = "json-vector"
        ranked.append(enriched)
    ranked.sort(key=lambda item: item.get("_vector_score", 0.0), reverse=True)
    return ranked[:top_k], "vector retrieval available"


def _with_rank_scores(chunks: list[dict], source: str) -> list[dict]:
    if not chunks:
        return []
    max_rank = len(chunks)
    enriched = []
    for index, chunk in enumerate(chunks):
        item = dict(chunk)
        item.setdefault("_score", float(max_rank - index))
        item["_retrieval_source"] = source
        enriched.append(item)
    return enriched


def _merge_ranked_results(bm25_chunks: list[dict], vector_chunks: list[dict], top_k: int) -> list[dict]:
    scores: dict[str, dict] = {}
    for chunk in bm25_chunks:
        item = scores.setdefault(chunk["id"], {"chunk": dict(chunk), "bm25": 0.0, "vector": 0.0})
        item["bm25"] = max(item["bm25"], _normalize_score(chunk.get("_score", 0.0), bm25_chunks))
    for chunk in vector_chunks:
        item = scores.setdefault(chunk["id"], {"chunk": dict(chunk), "bm25": 0.0, "vector": 0.0})
        item["vector"] = max(item["vector"], _normalize_score(chunk.get("_vector_score", 0.0), vector_chunks))

    merged = []
    for item in scores.values():
        combined = 0.65 * item["bm25"] + 0.35 * item["vector"]
        chunk = item["chunk"]
        chunk["_combined_score"] = combined
        chunk["_bm25_score_norm"] = item["bm25"]
        chunk["_vector_score_norm"] = item["vector"]
        merged.append(chunk)
    merged.sort(key=lambda chunk: chunk.get("_combined_score", 0.0), reverse=True)
    return merged[:top_k]


def _normalize_score(score: float, chunks: list[dict]) -> float:
    max_score = max((float(chunk.get("_score", chunk.get("_vector_score", 0.0))) for chunk in chunks), default=0.0)
    if max_score <= 0:
        return 0.0
    return float(score) / max_score
