from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CATALOG_ROOT = PROJECT_ROOT / "knowledge_corpus" / "experimental_assets"
CATALOG_PATH = CATALOG_ROOT / "catalog.json"


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Any]:
    if not CATALOG_PATH.is_file():
        return {
            "schema_version": "1.0",
            "status": "not-built",
            "topics": [],
            "assets": [],
        }
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def catalog_status() -> dict[str, Any]:
    payload = load_catalog()
    assets = payload.get("assets", [])
    return {
        "status": payload.get("status", "ready" if assets else "empty"),
        "asset_count": len(assets),
        "topic_count": len(payload.get("topics", [])),
        "reviewed_count": sum(
            item.get("review_status") in {"reviewed", "approved"} for item in assets
        ),
    }


def resolve_assets(
    evidence_ids: list[str] | None = None,
    source_ids: list[str] | None = None,
    *,
    limit: int = 8,
    query_text: str = "",
) -> list[dict[str, Any]]:
    evidence_ids = [item for item in (evidence_ids or []) if item]
    source_ids = set(item for item in (source_ids or []) if item)
    for evidence_id in evidence_ids:
        source_ids.update(_matching_source_ids(evidence_id))

    catalog_assets = load_catalog().get("assets", [])
    matched_assets: list[dict[str, Any]] = []
    for asset in catalog_assets:
        linked_sources = set(asset.get("linked_source_ids", []))
        linked_evidence = set(asset.get("linked_evidence_ids", []))
        if source_ids.intersection(linked_sources) or linked_evidence.intersection(evidence_ids):
            matched_assets.append(asset)

    condition_query = parse_condition_query(query_text)
    target_topic = condition_query["target_topic"]
    if target_topic:
        # Precise experiment queries should remain useful even when a broad
        # knowledge chunk did not carry the experimental source id.
        known_ids = {asset.get("asset_id") for asset in matched_assets}
        matched_assets.extend(
            asset
            for asset in catalog_assets
            if asset.get("topic") == target_topic
            and asset.get("asset_id") not in known_ids
        )

    if query_text.strip():
        matched_assets = sorted(
            enumerate(matched_assets),
            key=lambda item: (-_asset_query_score(item[1], query_text), item[0]),
        )
        matched_assets = [item for _, item in matched_assets]

    condition_group = _select_condition_group(matched_assets, condition_query, query_text)
    if condition_group:
        matched_assets = condition_group

    selected: list[dict[str, Any]] = []
    topic_counts: dict[str, int] = {}
    grouped_topic = target_topic if condition_group else ""
    for asset in matched_assets:
        topic = asset.get("topic", "other")
        if topic != grouped_topic and topic_counts.get(topic, 0) >= 4:
            continue
        selected.append(_public_asset(asset))
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
        if len(selected) >= max(1, min(limit, 20)):
            break
    return selected


def parse_condition_query(query_text: str) -> dict[str, Any]:
    """Extract explicit experimental conditions without inferring missing values."""
    normalized = query_text.lower()
    loads = _numbers_before_unit(normalized, r"(?:n|牛)(?![a-z])")
    distances = _numbers_before_unit(normalized, r"(?:m|米)(?![a-z])")
    durations = _numbers_before_unit(normalized, r"(?:h|小时)(?![a-z])")
    compact = normalized.replace(" ", "")
    load_matrix_signal = (
        bool(loads and distances)
        or any(
            marker in compact
            for marker in (
                "往复摩擦",
                "载荷-距离",
                "载荷距离",
                "不同载荷",
                "滑动距离",
                "磨损量和硬度",
                "磨损和硬度",
            )
        )
    )
    uv_signal = (
        "紫外" in compact
        or bool(durations and "老化" in compact)
        or ("亮度" in compact and "老化" in compact)
        or "同尺度比较" in compact
    )
    target_topic = ""
    if uv_signal:
        target_topic = "uv_aging_wear_morphology"
    elif load_matrix_signal:
        target_topic = "load_distance_morphology_matrix"

    return {
        "normal_load_N": loads,
        "sliding_distance_m": distances,
        "aging_duration_h": durations,
        "range_or_sequence": any(
            marker in compact
            for marker in ("到", "至", "范围", "序列", "增加", "变化", "趋势", "不同距离", "五个距离")
        ),
        "comparison": any(
            marker in compact
            for marker in ("比较", "对比", "不同视野", "摩擦前与摩擦后", "摩擦前和摩擦后")
        ),
        "target_topic": target_topic,
    }


def condition_match_strategy(condition_query: dict[str, Any]) -> str:
    if not condition_query.get("target_topic"):
        return "source-linked-ranking"
    if condition_query.get("range_or_sequence") or condition_query.get("comparison"):
        return "exact-condition-group"
    if any(
        condition_query.get(key)
        for key in ("normal_load_N", "sliding_distance_m", "aging_duration_h")
    ):
        return "exact-condition"
    return "topic-constrained-ranking"


def _numbers_before_unit(text: str, unit_pattern: str) -> list[float]:
    number = r"\d+(?:\.\d+)?"
    separators = r"[,，、/和与及到至~～\-]"
    pattern = re.compile(
        rf"((?:{number}\s*{separators}\s*)*{number})\s*{unit_pattern}",
        re.IGNORECASE,
    )
    values: list[float] = []
    for match in pattern.finditer(text):
        for raw in re.findall(number, match.group(1)):
            value = float(raw)
            if value not in values:
                values.append(value)
    return values


def _select_condition_group(
    assets: list[dict[str, Any]], condition_query: dict[str, Any], query_text: str
) -> list[dict[str, Any]]:
    topic = condition_query.get("target_topic")
    if topic == "load_distance_morphology_matrix":
        return _select_load_distance_group(assets, condition_query, query_text)
    if topic == "uv_aging_wear_morphology":
        return _select_uv_group(assets, condition_query, query_text)
    return []


def _select_load_distance_group(
    assets: list[dict[str, Any]], condition_query: dict[str, Any], query_text: str
) -> list[dict[str, Any]]:
    matrix = [
        asset
        for asset in assets
        if asset.get("topic") == "load_distance_morphology_matrix"
        and asset.get("modality") == "optical_image"
    ]
    loads = condition_query["normal_load_N"]
    distances = condition_query["sliding_distance_m"]
    sequence = condition_query["range_or_sequence"]

    def matches(asset: dict[str, Any]) -> bool:
        condition = asset.get("condition", {})
        load = float(condition.get("normal_load_N", -1))
        distance = float(condition.get("sliding_distance_m", -1))
        load_match = not loads or load in loads
        if distances and sequence and len(loads) == 1 and len(distances) >= 2:
            distance_match = min(distances) <= distance <= max(distances)
        else:
            distance_match = not distances or distance in distances
        return load_match and distance_match

    selected = [asset for asset in matrix if matches(asset)]
    selected.sort(
        key=lambda asset: (
            float(asset.get("condition", {}).get("normal_load_N", 0)),
            float(asset.get("condition", {}).get("sliding_distance_m", 0)),
        )
    )
    trend = next(
        (
            asset
            for asset in assets
            if asset.get("topic") == "load_distance_morphology_matrix"
            and asset.get("asset_id") == "LYQ-LOAD-MATRIX-TREND-01"
        ),
        None,
    )
    if not selected:
        return [trend] if trend is not None else []
    if not loads and not distances:
        return ([trend] if trend is not None else []) + selected

    exact_single = len(loads) == 1 and len(distances) == 1 and not sequence
    if exact_single:
        selected.sort(key=lambda asset: -_asset_query_score(asset, query_text))

    if trend is not None:
        selected.append(trend)
    return selected


def _select_uv_group(
    assets: list[dict[str, Any]], condition_query: dict[str, Any], query_text: str
) -> list[dict[str, Any]]:
    uv_assets = [asset for asset in assets if asset.get("topic") == "uv_aging_wear_morphology"]
    durations = condition_query["aging_duration_h"]
    if durations:
        uv_assets = [
            asset
            for asset in uv_assets
            if float(asset.get("condition", {}).get("aging_duration_h", -1)) in durations
        ]
    if not uv_assets:
        return []

    compact = query_text.lower().replace(" ", "")
    if not durations and "亮度" in compact:
        selected: list[dict[str, Any]] = []
        available_durations = sorted(
            {
                float(asset.get("condition", {}).get("aging_duration_h", -1))
                for asset in uv_assets
            }
        )
        for duration in available_durations:
            candidates = [
                asset
                for asset in uv_assets
                if float(asset.get("condition", {}).get("aging_duration_h", -1)) == duration
                and "摩擦前" not in asset.get("title", "")
                and "磨屑" not in asset.get("title", "")
            ]
            if candidates:
                selected.append(candidates[0])
        return selected
    if len(durations) > 1:
        # Cross-duration comparison uses one post-wear representative per
        # duration and avoids treating a pre-friction image as post-wear data.
        selected: list[dict[str, Any]] = []
        for duration in durations:
            candidates = [
                asset
                for asset in uv_assets
                if float(asset.get("condition", {}).get("aging_duration_h", -1)) == duration
                and "摩擦前" not in asset.get("title", "")
                and "磨屑" not in asset.get("title", "")
            ]
            if candidates:
                selected.append(candidates[0])
        return selected

    if condition_query["comparison"] or "不同视野" in compact:
        return uv_assets
    return sorted(uv_assets, key=lambda asset: -_asset_query_score(asset, query_text))


def _asset_query_score(asset: dict[str, Any], query_text: str) -> float:
    query = query_text.lower().replace(" ", "")
    searchable = json.dumps(
        {
            "title": asset.get("title", ""),
            "condition": asset.get("condition", {}),
            "labels": asset.get("labels", []),
            "observation": asset.get("observation", ""),
            "asset_id": asset.get("asset_id", ""),
        },
        ensure_ascii=False,
    ).lower().replace(" ", "")
    score = 0.0
    condition = asset.get("condition", {})
    for value in re.findall(r"(\d+(?:\.\d+)?)n", query):
        if float(condition.get("normal_load_N", -1)) == float(value):
            score += 12.0
    for value in re.findall(r"(\d+(?:\.\d+)?)m(?:\b|$)", query):
        if float(condition.get("sliding_distance_m", -1)) == float(value):
            score += 12.0
    for value in re.findall(r"(\d+(?:\.\d+)?)h", query):
        if float(condition.get("aging_duration_h", -1)) == float(value):
            score += 12.0
    for number in set(re.findall(r"\d+(?:\.\d+)?", query)):
        if number in searchable:
            score += 5.0
    for keyword in (
        "紫外老化",
        "热氧老化",
        "磨屑",
        "摩擦前",
        "摩擦后",
        "磨损形貌",
        "光学形貌",
        "趋势",
        "磨损量",
        "硬度",
        "载荷",
        "距离",
        "交互效应",
        "变量控制",
        "代表图",
        "偏磨",
        "实胎",
    ):
        if keyword in query and keyword in searchable:
            score += 3.0
    return score


def list_assets(topic: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    assets = load_catalog().get("assets", [])
    if topic:
        assets = [item for item in assets if item.get("topic") == topic]
    return [_public_asset(item) for item in assets[: max(1, min(limit, 100))]]


def get_asset(asset_id: str) -> dict[str, Any] | None:
    for asset in load_catalog().get("assets", []):
        if asset.get("asset_id") == asset_id:
            return _public_asset(asset)
    return None


def media_path(asset_id: str) -> Path | None:
    asset = get_asset(asset_id)
    if asset is None:
        return None
    candidate = (CATALOG_ROOT / asset["media_path"]).resolve()
    try:
        candidate.relative_to(CATALOG_ROOT.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def clear_catalog_cache() -> None:
    load_catalog.cache_clear()


def _matching_source_ids(evidence_id: str) -> set[str]:
    matches: set[str] = set()
    for asset in load_catalog().get("assets", []):
        for source_id in asset.get("linked_source_ids", []):
            if evidence_id == source_id or evidence_id.startswith(f"{source_id}-"):
                matches.add(source_id)
    return matches


def _public_asset(asset: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "asset_id",
        "experiment_id",
        "sample_id",
        "domain",
        "topic",
        "title",
        "modality",
        "media_type",
        "media_path",
        "source_reference",
        "source_sha256",
        "derived_sha256",
        "condition",
        "labels",
        "severity",
        "observation",
        "training_use",
        "review_status",
        "authorization_status",
        "linked_source_ids",
        "linked_evidence_ids",
        "limitations",
    }
    return {key: value for key, value in asset.items() if key in allowed}
