from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from app.models.schemas import TrainingDomain

APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = APP_DIR / "data"

DOMAIN_TITLES = {
    "tire": "航空轮胎胎面橡胶损伤分析",
    "brake": "航空刹车片摩擦磨损与失效分析",
    "composite": "飞机复合材料板损伤分析",
}


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


@lru_cache
def load_profiles() -> list[dict[str, Any]]:
    return _read_json(DATA_DIR / "profiles.json")


@lru_cache
def load_questions() -> list[dict[str, Any]]:
    return _read_json(DATA_DIR / "questions.json")


@lru_cache
def load_knowledge_base() -> dict[str, dict[str, Any]]:
    return {
        "tire": _read_json(DATA_DIR / "knowledge_tire.json"),
        "brake": _read_json(DATA_DIR / "knowledge_brake.json"),
        "composite": _read_json(DATA_DIR / "knowledge_composite.json"),
    }


@lru_cache
def load_demo_sessions() -> list[dict[str, Any]]:
    return _read_json(DATA_DIR / "demo_sessions.json")


def get_profile(profile_id: str) -> dict[str, Any]:
    for profile in load_profiles():
        if profile["profile_id"] == profile_id:
            return profile
    raise KeyError(f"Unknown profile_id: {profile_id}")


def get_questions_by_domain(domain: TrainingDomain) -> list[dict[str, Any]]:
    return [question for question in load_questions() if question["domain"] == domain]


def get_knowledge_domain(domain: TrainingDomain) -> dict[str, Any]:
    knowledge = load_knowledge_base()
    if domain not in knowledge:
        raise KeyError(f"Unknown domain: {domain}")
    return knowledge[domain]


def get_domains() -> list[dict[str, str]]:
    return [
        {
            "domain": domain,
            "title": item["title"],
            "summary": item["summary"],
        }
        for domain, item in load_knowledge_base().items()
    ]


def get_data_status() -> dict[str, Any]:
    knowledge = load_knowledge_base()
    return {
        "profiles": len(load_profiles()),
        "questions": len(load_questions()),
        "knowledge_domains": list(knowledge.keys()),
        "knowledge_chunks": {
            domain: len(item.get("chunks", []))
            for domain, item in knowledge.items()
        },
        "demo_sessions": len(load_demo_sessions()),
    }


# Backward-compatible aliases used by the first MVP.
load_learners = load_profiles


def get_domain(domain: TrainingDomain) -> dict[str, Any]:
    item = get_knowledge_domain(domain)
    legacy = dict(item)
    legacy["knowledge_chunks"] = item.get("chunks", [])
    legacy["diagnostic_questions"] = get_questions_by_domain(domain)
    return legacy
