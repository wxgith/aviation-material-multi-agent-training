import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEAM_ROOT = PROJECT_ROOT / "knowledge_corpus" / "raw_docs" / "team_tire"


def _records() -> dict:
    path = TEAM_ROOT / "data" / "tire_lyq_friction_records.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_lyq_structured_records_cover_temperature_load_and_contact_modes():
    payload = _records()
    temperatures = payload["temperature_experiment"]["conditions"]

    assert [item["ambient_temperature_C"] for item in temperatures] == [15, 40, 60, 80, 100]
    assert all(len(item["temperature_curves"]) == 3 for item in temperatures)
    assert len(payload["load_distance_experiment"]) == 15
    assert len(payload["contact_friction_curves"]) == 18
    assert set(payload["contact_modes"]) == {"cylinder_flat", "sphere_flat", "ring_block"}
    assert len({item["evidence_id"] for item in payload["load_distance_experiment"]}) == 15


def test_lyq_image_evidence_is_condition_bound_and_present():
    path = TEAM_ROOT / "data" / "tire_lyq_image_evidence.json"
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert len(payload["images"]) == 17
    for image in payload["images"]:
        assert image["condition"]
        assert (TEAM_ROOT / image["relative_path"]).is_file()
        assert len(image["sha256"]) == 64
