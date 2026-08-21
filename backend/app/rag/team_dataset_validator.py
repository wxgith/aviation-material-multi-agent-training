from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET_ROOT = PROJECT_ROOT / "knowledge_corpus" / "raw_docs" / "team_tire"

EXPERIMENT_TEMPLATE = "航空轮胎热氧老化与滑动磨损实验记录模板.xlsx"
IMAGE_TEMPLATE = "损伤图像与案例标注模板.xlsx"

REQUIRED_PATHS = [
    "README.md",
    "实验说明模板.md",
    "数据脱敏与命名规范.md",
    "dataset_manifest.template.json",
    f"data/{EXPERIMENT_TEMPLATE}",
    f"data/{IMAGE_TEMPLATE}",
    "images/SEM",
    "images/optical",
    "images/damage_cases",
    "attachments",
]

EXPECTED_EXPERIMENT_SHEETS = {
    "使用说明",
    "样品信息",
    "老化工况",
    "磨损原始记录",
    "结果汇总",
    "数据字典",
}
EXPECTED_IMAGE_SHEETS = {
    "使用说明",
    "图像索引",
    "损伤标注",
    "案例记录",
    "数据字典",
}


def validate_team_dataset(root: Path = DEFAULT_DATASET_ROOT) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    for relative_path in REQUIRED_PATHS:
        if not (root / relative_path).exists():
            errors.append(f"missing required path: {relative_path}")

    template_manifest_path = root / "dataset_manifest.template.json"
    if template_manifest_path.exists():
        try:
            json.loads(template_manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid manifest template: {exc}")

    _validate_workbook_sheets(
        root / "data" / EXPERIMENT_TEMPLATE,
        EXPECTED_EXPERIMENT_SHEETS,
        errors,
    )
    _validate_workbook_sheets(
        root / "data" / IMAGE_TEMPLATE,
        EXPECTED_IMAGE_SHEETS,
        errors,
    )

    actual_manifest_path = root / "dataset_manifest.json"
    mode = "dataset" if actual_manifest_path.exists() else "template"
    if actual_manifest_path.exists():
        try:
            manifest = json.loads(actual_manifest_path.read_text(encoding="utf-8"))
            _validate_manifest(manifest, root, errors, warnings)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid dataset_manifest.json: {exc}")
    else:
        warnings.append(
            "dataset_manifest.json not found; copy dataset_manifest.template.json when real data collection starts"
        )

    image_count = sum(
        1
        for directory in [root / "images" / "SEM", root / "images" / "optical", root / "images" / "damage_cases"]
        if directory.exists()
        for path in directory.iterdir()
        if path.is_file()
    )
    return {
        "status": "ready" if not errors else "invalid",
        "mode": mode,
        "dataset_root": str(root),
        "errors": errors,
        "warnings": warnings,
        "image_files": image_count,
        "approved_for_rag": mode == "dataset" and not errors and not warnings,
    }


def _validate_manifest(
    manifest: dict, root: Path, errors: list[str], warnings: list[str]
) -> None:
    required_fields = {
        "dataset_id",
        "title",
        "domain",
        "owner_code",
        "authorization_status",
        "contains_personal_data",
        "contains_restricted_commercial_data",
        "files",
        "review",
        "ingestion",
    }
    missing = sorted(required_fields - set(manifest))
    if missing:
        errors.append(f"manifest missing fields: {', '.join(missing)}")
        return

    if manifest.get("domain") != "tire":
        errors.append("manifest domain must be tire")
    if manifest.get("contains_personal_data"):
        errors.append("personal data must be removed before ingestion")
    if manifest.get("contains_restricted_commercial_data"):
        errors.append("restricted commercial data cannot enter the competition corpus")

    authorization = manifest.get("authorization_status")
    allowed_authorizations = {"team_owned", "authorized", "public"}
    ingestion = manifest.get("ingestion") or {}
    review = manifest.get("review") or {}
    approved_for_rag = bool(ingestion.get("approved_for_rag"))
    if approved_for_rag and authorization not in allowed_authorizations:
        errors.append("RAG approval requires team_owned, authorized or public authorization")
    if approved_for_rag and review.get("review_status") != "approved":
        errors.append("RAG approval requires review.review_status=approved")
    if authorization in {"pending", "restricted"}:
        warnings.append(f"authorization_status={authorization}; dataset must not be indexed")

    files = manifest.get("files") or {}
    for key in ["experiment_workbook", "image_annotation_workbook", "experiment_description"]:
        relative_path = files.get(key)
        if not relative_path:
            errors.append(f"manifest files.{key} is required")
        elif not (root / relative_path).exists():
            errors.append(f"manifest file not found: {relative_path}")


def _validate_workbook_sheets(
    path: Path, expected: set[str], errors: list[str]
) -> None:
    if not path.exists():
        return
    try:
        sheets = _xlsx_sheet_names(path)
    except (OSError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        errors.append(f"invalid workbook {path.name}: {exc}")
        return
    missing = sorted(expected - sheets)
    if missing:
        errors.append(f"workbook {path.name} missing sheets: {', '.join(missing)}")


def _xlsx_sheet_names(path: Path) -> set[str]:
    with zipfile.ZipFile(path) as archive:
        workbook_xml = archive.read("xl/workbook.xml")
    root = ElementTree.fromstring(workbook_xml)
    namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    return {
        node.attrib["name"]
        for node in root.findall("main:sheets/main:sheet", namespace)
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the team tire experiment dataset package")
    parser.add_argument("--root", type=Path, default=DEFAULT_DATASET_ROOT)
    args = parser.parse_args()
    result = validate_team_dataset(args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
