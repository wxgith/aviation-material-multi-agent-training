import pytest

from app.rag.team_dataset_pipeline import (
    DEFAULT_DATASET_ROOT,
    load_team_dataset,
    render_dataset_markdown,
)


def test_template_workbooks_are_loaded_and_derived() -> None:
    manifest, dataset = load_team_dataset(
        DEFAULT_DATASET_ROOT,
        template_mode=True,
        include_demo=True,
    )

    assert manifest["domain"] == "tire"
    assert {key: len(rows) for key, rows in dataset.items()} == {
        "samples": 3,
        "aging_conditions": 3,
        "wear_records": 4,
        "images": 2,
        "annotations": 2,
        "cases": 1,
    }
    first_wear = dataset["wear_records"][0]
    assert first_wear["sliding_distance_m"] == 300
    assert first_wear["friction_coefficient"] == pytest.approx(0.6)
    assert first_wear["mass_loss_mg"] == 18


def test_template_markdown_keeps_evidence_ids_and_boundary() -> None:
    manifest, dataset = load_team_dataset(
        DEFAULT_DATASET_ROOT,
        template_mode=True,
        include_demo=True,
    )
    markdown = render_dataset_markdown(manifest, dataset)

    assert "DEMO-WEAR-20260810-001" in markdown
    assert "DEMO-IMG-001" in markdown
    assert "DEMO-CASE-TIRE-0001" in markdown
    assert "Evidence and safety boundary" in markdown


def test_approved_dataset_loads_without_demo_records() -> None:
    manifest, dataset = load_team_dataset(DEFAULT_DATASET_ROOT)

    assert manifest["authorization_status"] == "authorized"
    assert manifest["review"]["review_status"] == "approved"
    assert {key: len(rows) for key, rows in dataset.items()} == {
        "samples": 18,
        "aging_conditions": 9,
        "wear_records": 18,
        "images": 14,
        "annotations": 14,
        "cases": 7,
    }
    assert all(
        not str(next(iter(row.values()), "")).upper().startswith("DEMO-")
        for rows in dataset.values()
        for row in rows
    )


def test_approved_dataset_markdown_keeps_rxq_evidence_and_boundary() -> None:
    manifest, dataset = load_team_dataset(DEFAULT_DATASET_ROOT)
    markdown = render_dataset_markdown(manifest, dataset)

    assert "RXQ-WEAR-D028-S62" in markdown
    assert "RXQ-IMG-D028-S62-SEM-01" in markdown
    assert "RXQ-CASE-TIRE-D028" in markdown
    assert "airworthiness or maintenance conclusions" in markdown
