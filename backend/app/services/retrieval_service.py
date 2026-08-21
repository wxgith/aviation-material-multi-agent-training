import re

from app.evidence.catalog import parse_condition_query
from app.models.schemas import TrainingDomain
from app.services.data_loader import get_knowledge_domain


def retrieve_knowledge(
    domain: TrainingDomain,
    weak_points: list[str],
    learning_goal: str,
    learner_type: str,
    top_k: int = 5,
) -> list[dict]:
    knowledge = get_knowledge_domain(domain)
    chunks = knowledge.get("chunks", [])
    ranked = []

    condition_query = parse_condition_query(learning_goal)
    for chunk in chunks:
        score = 0
        tags = chunk.get("tags", [])
        content = chunk.get("content", "")
        title = chunk.get("title", "")

        for point in weak_points:
            if point in tags or any(tag in point or point in tag for tag in tags):
                score += 5
            if point and (point in title or point in content):
                score += 3

        for keyword in _goal_keywords(learning_goal):
            if keyword in tags:
                score += 2
            if keyword in title or keyword in content:
                score += 1

        if learner_type in chunk.get("applicable_learners", []):
            score += 2

        if chunk.get("source_type") == "practice_task":
            score += 1

        score += _experimental_condition_score(chunk, condition_query)

        ranked.append((score, chunk))

    ranked.sort(key=lambda item: item[0], reverse=True)
    selected = [chunk for score, chunk in ranked if score > 0][:top_k]
    if len(selected) < min(top_k, len(chunks)):
        selected_ids = {chunk["id"] for chunk in selected}
        for _, chunk in ranked:
            if chunk["id"] not in selected_ids:
                selected.append(chunk)
            if len(selected) >= top_k:
                break
    return selected


def _experimental_condition_score(chunk: dict, condition_query: dict) -> int:
    source_id = chunk.get("source_id", "")
    searchable = re.sub(
        r"\s+", "", f"{chunk.get('title', '')} {chunk.get('content', '')}"
    ).lower()
    score = 0
    target_topic = condition_query.get("target_topic")
    if target_topic == "load_distance_morphology_matrix" and source_id in {
        "team_tire_lyq_load_distance_matrix",
        "team_tire_lyq_contact_load_temperature_evidence",
    }:
        score += 30
    if target_topic == "uv_aging_wear_morphology" and source_id in {
        "team_tire_rxq_uv_wear_morphology",
        "team_tire_rxq_aging_multimodal_evidence",
    }:
        score += 30
    for value in condition_query.get("normal_load_N", []):
        if re.search(rf"(?<!\d){value:g}n(?!\w)", searchable):
            score += 6
    for value in condition_query.get("sliding_distance_m", []):
        if re.search(rf"(?<!\d){value:g}m(?!\w)", searchable):
            score += 6
    for value in condition_query.get("aging_duration_h", []):
        if re.search(rf"(?<!\d){value:g}h(?!\w)", searchable):
            score += 6
    return score


def _goal_keywords(learning_goal: str) -> list[str]:
    candidates = [
        "热氧老化",
        "滑动磨损",
        "胎面裂纹",
        "剥落",
        "耦合损伤",
        "损伤边界",
        "起降次数",
        "维护判读",
        "实验表征",
        "证据链",
        "高温摩擦",
        "热衰退",
        "磨损形貌",
        "紫外老化",
        "往复摩擦",
        "载荷",
        "滑动距离",
        "磨损量",
        "硬度",
        "摩擦前",
        "摩擦后",
        "磨屑",
        "氧化",
        "裂纹",
        "失效机理",
        "摩擦性能变化",
        "冲击损伤",
        "隐蔽损伤",
        "分层",
        "基体开裂",
        "纤维断裂",
        "无损检测",
        "无损检测图像判读",
        "表征",
        "对照组",
        "损伤扩展",
        "实操训练任务",
    ]
    selected = [keyword for keyword in candidates if keyword in learning_goal]
    if "无损检测" in learning_goal and "无损检测图像判读" not in selected:
        selected.append("无损检测图像判读")
    return selected
