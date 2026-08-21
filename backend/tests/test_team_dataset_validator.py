from pathlib import Path

from app.rag.team_dataset_validator import (
    DEFAULT_DATASET_ROOT,
    _validate_manifest,
    validate_team_dataset,
)


def test_team_tire_approved_dataset_package_is_ready():
    result = validate_team_dataset(DEFAULT_DATASET_ROOT)

    assert result["status"] == "ready"
    assert result["mode"] == "dataset"
    assert not result["errors"]
    assert not result["warnings"]
    assert result["image_files"] == 14
    assert result["approved_for_rag"] is True


def test_manifest_blocks_personal_and_unreviewed_data(tmp_path: Path):
    manifest = {
        "dataset_id": "TIRE-EXP-TEST-001",
        "title": "test",
        "domain": "tire",
        "owner_code": "TEAM-A",
        "authorization_status": "pending",
        "contains_personal_data": True,
        "contains_restricted_commercial_data": False,
        "files": {
            "experiment_workbook": "missing.xlsx",
            "image_annotation_workbook": "missing-images.xlsx",
            "experiment_description": "missing.md",
        },
        "review": {"review_status": "draft"},
        "ingestion": {"approved_for_rag": True},
    }
    errors: list[str] = []
    warnings: list[str] = []

    _validate_manifest(manifest, tmp_path, errors, warnings)

    assert any("personal data" in error for error in errors)
    assert any("RAG approval requires" in error for error in errors)
    assert any("file not found" in error for error in errors)
    assert warnings
