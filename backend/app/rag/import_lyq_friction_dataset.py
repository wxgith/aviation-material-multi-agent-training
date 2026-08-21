from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from datetime import date
from pathlib import Path
from statistics import mean
from typing import Any

from openpyxl import load_workbook


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CORPUS_ROOT = PROJECT_ROOT / "knowledge_corpus"
TEAM_ROOT = CORPUS_ROOT / "raw_docs" / "team_tire"
SOURCE_ROOT = Path("E:/梁永琦")
CURATED_ROOT = TEAM_ROOT / "pending_review" / "lyq_friction_experiments"
FORMAL_ROOT = TEAM_ROOT / "data"
IMAGE_ROOT = TEAM_ROOT / "images" / "lyq"
PARSED_ROOT = CORPUS_ROOT / "parsed_docs"
REGISTRY_PATH = CORPUS_ROOT / "source_registry.json"

DATASET_ID = "TIRE-EXP-LYQ-FRICTION-001"
SOURCE_ID = "team_tire_lyq_contact_load_temperature_evidence"
REVIEW_DATE = date(2026, 8, 4).isoformat()
FORMAL_RECORDS = FORMAL_ROOT / "tire_lyq_friction_records.json"
FORMAL_IMAGES = FORMAL_ROOT / "tire_lyq_image_evidence.json"
PARSED_DOCUMENT = PARSED_ROOT / f"{SOURCE_ID}.md"

TEMPERATURE_SAMPLE_GROUPS = {
    15: [1, 2, 3],
    40: [4, 5, 6],
    60: [7, 8, 9],
    80: [10, 11, 12],
    100: [13, 14, 15],
}
TEMPERATURE_FRICTION_MEANS = {
    15: 0.6872581395348846,
    40: 0.700527,
    60: 0.7267932692307683,
    80: 0.7616387921022056,
    100: 0.7662040094339623,
}
TEMPERATURE_WEAR_RATE_G_PER_M = {
    15: 0.000269444,
    40: 0.000408333,
    60: 0.000441667,
    80: 0.00055,
    100: 0.000536111,
}
TEMPERATURE_HARDNESS_HA = {
    15: 65.6625,
    40: 67.4,
    60: 67.5,
    80: 66.75,
    100: 68.7875,
}

LOAD_WEAR_LOSS_G = {
    20: {40: 0.0125, 50: 0.018, 60: 0.0365},
    40: {40: 0.0155, 50: 0.0295, 60: 0.0685},
    80: {40: 0.037, 50: 0.0505, 60: 0.1025},
    120: {40: 0.0445, 50: 0.089, 60: 0.139},
    160: {40: 0.06, 50: 0.1205, 60: 0.1605},
}
LOAD_HARDNESS_HA = {
    0: {40: 72.0, 50: 72.0, 60: 72.0},
    20: {40: 65.275, 50: 60.62857, 60: 58.88571},
    40: {40: 63.92857, 50: 58.9, 60: 57.68571},
    80: {40: 60.56667, 50: 55.14286, 60: 53.11429},
    120: {40: 56.37143, 50: 53.38333, 60: 49.75},
    160: {40: 52.55714, 50: 51.22857, 60: 46.57143},
}

CONTACT_MODES = {
    "cylinder_flat": {
        "name": "柱-面往复接触",
        "loads_N": [40, 50, 60],
        "contact_pressures_MPa": [1.2, 1.5, 1.8],
        "distances_m": [20, 40, 80, 120, 160],
        "counterface": "直径6.5 mm金属砂柱，底部220目砂纸",
        "specimen_mm": [40, 10, 10],
        "motion": "10 mm往复位移，3.3 Hz",
        "training_scope": "高载低速周期滑移、疲劳裂纹和接触应力效应",
    },
    "sphere_flat": {
        "name": "球-面往复接触",
        "loads_N": [40, 50, 60],
        "contact_pressures_MPa": [3.0, 3.2, 3.6],
        "distances_m": [40, 80, 120],
        "counterface": "金属砂球",
        "specimen_mm": [40, 10, 10],
        "motion": "10 mm往复位移，3.3 Hz",
        "training_scope": "非均匀压力与局部应力集中",
    },
    "ring_block": {
        "name": "环-块单向滑动接触",
        "loads_N": [50, 70, 90],
        "contact_pressures_MPa": [0.77, 0.92, 1.01],
        "distances_m": [628, 1257, 1885],
        "counterface": "直径40 mm、80目砂轮",
        "specimen_mm": [19, 8, 10],
        "motion": "200 r/min，线速度约0.42 m/s",
        "training_scope": "单向滑动、较长距离与着陆滑跑形貌模拟",
    },
}


def main() -> None:
    _assert_sources()
    copied = _curate_sources()
    temperature_records = _temperature_records()
    contact_curves = _contact_curve_records()
    load_records = _load_records()
    image_records = _copy_image_evidence()
    payload = _write_formal_records(temperature_records, contact_curves, load_records)
    FORMAL_IMAGES.write_text(
        json.dumps({"dataset_id": DATASET_ID, "images": image_records}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_manifest(copied, payload, image_records)
    _write_markdown(payload, image_records)
    _register_source()
    print(
        json.dumps(
            {
                "status": "prepared",
                "dataset_id": DATASET_ID,
                "curated_files": len(copied),
                "temperature_conditions": len(temperature_records),
                "load_distance_records": len(load_records),
                "contact_curves": len(contact_curves),
                "image_evidence": len(image_records),
                "formal_records": str(FORMAL_RECORDS),
                "parsed_document": str(PARSED_DOCUMENT),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _assert_sources() -> None:
    required = [
        SOURCE_ROOT / "不同接触方式" / "标号.xlsx",
        SOURCE_ROOT / "不同接触方式" / "磨损率.xlsx",
        SOURCE_ROOT / "不同载荷往复实验" / "不同载荷往复补充.zip",
        SOURCE_ROOT / "温度" / "标号.xlsx",
        SOURCE_ROOT / "温度" / "硬度和磨损率.xlsx",
        SOURCE_ROOT / "梁永琦转胡老师" / "S20220202027-梁永琦-航空轮胎胎面橡胶损伤分析与滑动磨损实验研究.docx",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing LYQ source files: " + ", ".join(missing))


def _curate_sources() -> list[dict[str, Any]]:
    selections: list[tuple[Path, Path]] = [
        (SOURCE_ROOT / "不同接触方式" / "标号.xlsx", Path("data/contact_sample_map.xlsx")),
        (SOURCE_ROOT / "不同接触方式" / "磨损率.xlsx", Path("data/contact_reported_wear.xlsx")),
        (SOURCE_ROOT / "不同载荷往复实验" / "不同载荷往复补充.zip", Path("archives/reciprocating_load_supplement.zip")),
        (SOURCE_ROOT / "温度" / "标号.xlsx", Path("data/temperature_sample_map.xlsx")),
        (SOURCE_ROOT / "温度" / "硬度和磨损率.xlsx", Path("data/temperature_hardness_wear.xlsx")),
        (SOURCE_ROOT / "温度" / "摩擦系数" / "新建文件夹" / "平均值.xlsx", Path("data/temperature_friction_means.xlsx")),
    ]
    for sample in range(1, 16):
        selections.append(
            (
                SOURCE_ROOT / "温度" / "光学显微镜和温度" / f"{sample}.csv",
                Path("raw_curves/interface_temperature") / f"sample_{sample:02d}.csv",
            )
        )
    for mode in ("环块", "球面"):
        source_dir = SOURCE_ROOT / "不同接触方式" / "摩擦系数" / mode
        for path in sorted(source_dir.glob("*.txt")):
            selections.append((path, Path("raw_curves/contact_friction") / mode / path.name))
    inventory = []
    for source, relative in selections:
        if not source.is_file():
            continue
        target = CURATED_ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        inventory.append(
            {
                "source_path": str(source),
                "curated_path": relative.as_posix(),
                "size_bytes": target.stat().st_size,
                "sha256": _sha256(target),
            }
        )
    (CURATED_ROOT / "source_inventory.json").write_text(
        json.dumps({"dataset_id": DATASET_ID, "files": inventory}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return inventory


def _temperature_records() -> list[dict[str, Any]]:
    records = []
    curve_root = SOURCE_ROOT / "温度" / "光学显微镜和温度"
    for temperature, samples in TEMPERATURE_SAMPLE_GROUPS.items():
        curve_summaries = []
        for sample in samples:
            path = curve_root / f"{sample}.csv"
            with path.open("r", encoding="gb18030", newline="") as stream:
                rows = list(csv.reader(stream))[1:]
            values = [float(row[1]) for row in rows if len(row) > 1 and row[1]]
            curve_summaries.append(
                {
                    "sample_code": str(sample),
                    "source_csv": f"raw_curves/interface_temperature/sample_{sample:02d}.csv",
                    "points": len(values),
                    "maximum_interface_temperature_C": max(values),
                    "last_10pct_mean_temperature_C": mean(values[int(len(values) * 0.9) :]),
                }
            )
        records.append(
            {
                "evidence_id": f"LYQ-TEMP-T{temperature:03d}",
                "ambient_temperature_C": temperature,
                "load_N": 50,
                "contact_pressure_MPa": 1.5,
                "sliding_distance_m": 120,
                "stroke_mm": 10,
                "frequency_Hz": 3.3,
                "replicates": 3,
                "mean_friction_coefficient": TEMPERATURE_FRICTION_MEANS[temperature],
                "wear_rate_g_per_m": TEMPERATURE_WEAR_RATE_G_PER_M[temperature],
                "workbook_reported_hardness_HA": TEMPERATURE_HARDNESS_HA[temperature],
                "maximum_interface_temperature_C": max(
                    item["maximum_interface_temperature_C"] for item in curve_summaries
                ),
                "temperature_curves": curve_summaries,
            }
        )
    return records


def _contact_curve_records() -> list[dict[str, Any]]:
    records = []
    expected = {
        "环块": {"5025", "5050", "5075", "7025", "7050", "7075", "9025", "9050", "9067"},
        "球面": {"4020", "4040", "4060", "5020", "5040", "5060", "6020", "6040", "6060"},
    }
    for mode, stems in expected.items():
        source_dir = SOURCE_ROOT / "不同接触方式" / "摩擦系数" / mode
        for stem in sorted(stems):
            path = source_dir / f"{stem}.txt"
            if not path.is_file():
                path = source_dir / f"{stem}.1.txt"
            if not path.is_file():
                continue
            text = path.read_text(encoding="gb18030")
            metadata = {
                key: value
                for key, value in re.findall(r'^"([^"]+)","([^"]*)"$', text, flags=re.MULTILINE)
            }
            coefficients = []
            for line in text.splitlines():
                parts = line.split(",")
                if len(parts) not in {2, 5}:
                    continue
                try:
                    coefficients.append(float(parts[1]))
                except ValueError:
                    continue
            stable = coefficients[max(1, int(len(coefficients) * 0.1)) :]
            load = int(float(metadata.get("加载载荷", stem[:2])))
            duration = int(float(metadata.get("试验时间", stem[2:])))
            record = {
                "evidence_id": f"LYQ-CONTACT-{'RB' if mode == '环块' else 'SF'}-{stem}",
                "contact_mode": "ring_block" if mode == "环块" else "sphere_flat",
                "load_N": load,
                "duration_min": duration,
                "speed_rpm": float(metadata.get("运行速度", 200)),
                "source_file": f"raw_curves/contact_friction/{mode}/{path.name}",
                "curve_points": len(coefficients),
                "stable_mean_friction_coefficient": mean(stable) if stable else None,
                "maximum_friction_coefficient": max(coefficients) if coefficients else None,
                "qc_flag": "partial_duration" if mode == "环块" and stem == "9067" else "source_record",
            }
            records.append(record)
    return records


def _load_records() -> list[dict[str, Any]]:
    pressure = {40: 1.2, 50: 1.5, 60: 1.8}
    records = []
    for distance, loads in LOAD_WEAR_LOSS_G.items():
        for load, wear_loss in loads.items():
            records.append(
                {
                    "evidence_id": f"LYQ-LOAD-P{pressure[load]:.1f}-D{distance:03d}",
                    "contact_mode": "cylinder_flat",
                    "load_N": load,
                    "contact_pressure_MPa": pressure[load],
                    "sliding_distance_m": distance,
                    "reported_wear_loss_g": wear_loss,
                    "reported_hardness_HA": LOAD_HARDNESS_HA[distance][load],
                    "stroke_mm": 10,
                    "frequency_Hz": 3.3,
                }
            )
    return records


def _copy_image_evidence() -> list[dict[str, Any]]:
    selections = [
        (SOURCE_ROOT / "温度" / "SEM" / "3-_1.jpeg", "LYQ-IMG-T015-SEM-01.jpeg", "SEM", "15 °C, sample 3, 2000x"),
        (SOURCE_ROOT / "温度" / "SEM" / "7-_1.jpeg", "LYQ-IMG-T060-SEM-01.jpeg", "SEM", "60 °C, sample 7"),
        (SOURCE_ROOT / "温度" / "SEM" / "10_1.jpeg", "LYQ-IMG-T080-SEM-01.jpeg", "SEM", "80 °C, sample 10"),
        (SOURCE_ROOT / "温度" / "3D" / "3D" / "15.tif", "LYQ-IMG-T015-3DOM-01.tif", "3D-OM", "15 °C"),
        (SOURCE_ROOT / "温度" / "3D" / "3D" / "60.tif", "LYQ-IMG-T060-3DOM-01.tif", "3D-OM", "60 °C"),
        (SOURCE_ROOT / "温度" / "3D" / "3D" / "100.tif", "LYQ-IMG-T100-3DOM-01.tif", "3D-OM", "100 °C"),
        (SOURCE_ROOT / "不同载荷往复实验" / "超景深（西南交大）" / "10-1.jpg", "LYQ-IMG-P12-D160-OM-01.jpg", "optical", "1.2 MPa, 160 m"),
        (SOURCE_ROOT / "不同载荷往复实验" / "超景深（西南交大）" / "19-1.jpg", "LYQ-IMG-P15-D160-OM-01.jpg", "optical", "1.5 MPa, 160 m"),
        (SOURCE_ROOT / "不同载荷往复实验" / "超景深（西南交大）" / "29-1.jpg", "LYQ-IMG-P18-D160-OM-01.jpg", "optical", "1.8 MPa, 160 m"),
    ]
    plot_root = SOURCE_ROOT / "温度" / "origin图"
    for path in sorted(plot_root.glob("*.png")):
        selections.append((path, f"LYQ-PLOT-{len(selections) + 1:02d}.png", "plot", path.stem))
    IMAGE_ROOT.mkdir(parents=True, exist_ok=True)
    records = []
    for index, (source, name, image_type, condition) in enumerate(selections, start=1):
        if not source.is_file():
            continue
        target = IMAGE_ROOT / name
        shutil.copy2(source, target)
        records.append(
            {
                "image_id": f"LYQ-IMG-{index:03d}",
                "file_name": name,
                "relative_path": target.relative_to(TEAM_ROOT).as_posix(),
                "image_type": image_type,
                "condition": condition,
                "sha256": _sha256(target),
                "authorization_status": "authorized",
                "annotation_status": "condition_bound; morphology label requires expert review",
            }
        )
    return records


def _write_formal_records(
    temperature_records: list[dict[str, Any]],
    contact_curves: list[dict[str, Any]],
    load_records: list[dict[str, Any]],
) -> dict[str, Any]:
    FORMAL_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {
        "dataset_id": DATASET_ID,
        "title": "航空轮胎胎面橡胶多接触方式、载荷与温度摩擦磨损实验",
        "domain": "tire",
        "material": "anonymized_commercial_aircraft_tire_tread_rubber",
        "authorization_status": "authorized",
        "equipment": {
            "tribometer": "CFT-I",
            "thermal_camera": "FOTRIC-628CH",
            "optical_microscope": "OLYMPUS SZX7",
            "profilometer": "BRUKER NPFLEX",
            "sem": "FEI Apreo 2C",
            "ftir": "Thermo Fisher Nicolet iS20",
        },
        "common_environment": {"temperature_C": "25±1", "relative_humidity_pct": "45±3"},
        "contact_modes": CONTACT_MODES,
        "temperature_experiment": {
            "contact_mode": "cylinder_flat",
            "conditions": temperature_records,
            "scope_note": "正式论文组为15、40、60、80、100 °C；30、50、70、90、120 °C辅助点未纳入正式趋势记录。",
        },
        "load_distance_experiment": load_records,
        "contact_friction_curves": contact_curves,
        "validated_findings": [
            "接触应力由1.2 MPa增至1.8 MPa时，磨损和撕裂加剧，界面稳态温度约由87 °C升至102 °C。",
            "环境温度由15 °C升至100 °C时，界面最高温度约由80 °C升至126 °C，磨损率先升高后趋稳。",
            "初期以平行滑动方向的犁沟和磨粒磨损为主，距离、应力或温度增加后出现垂直滑动方向的山脊状条纹，转为磨粒-疲劳复合磨损。",
            "FT-IR证据支持磨损表面同时存在分子链断裂与氧化降解，高温下氧化降解作用增强。",
            "柱-面适合周期疲劳训练，球-面适合局部应力集中训练，环-块更接近单向滑跑与长距离摩擦。",
        ],
        "source_conflicts": [
            "环-块标号表写75 N，而论文、磨损表与70xx曲线文件使用70 N；正式记录采用交叉证据更充分的70 N。",
            "环-块90 N最长曲线文件名为9067且元数据显示67 min，短于方案75 min，标记为partial_duration。",
            "温度标号表沿用“50 N、200 r/min、60 min”文字，而论文明确温度研究为柱-面往复3.3 Hz；正式工况采用论文方法，表格差异保留。",
            "不同接触方式磨损表未标明数值单位，因此仅作为原始附件保存，不用于定量生成。",
        ],
        "safety_boundary": "实验室小试结果用于教学、机理分析和工况比较，不直接构成航空轮胎维修或适航放行限值。",
    }
    FORMAL_RECORDS.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _write_manifest(copied: list[dict], payload: dict, images: list[dict]) -> None:
    manifest = {
        "dataset_id": DATASET_ID,
        "title": payload["title"],
        "domain": "tire",
        "owner_code": "TEAM-LYQ",
        "authorization_status": "authorized",
        "contains_personal_data": False,
        "contains_restricted_commercial_data": False,
        "privacy_note": "论文姓名、学号和完整配方不进入RAG；材料以匿名商用航空轮胎胎面橡胶表示。",
        "record_counts": {
            "curated_source_files": len(copied),
            "temperature_conditions": len(payload["temperature_experiment"]["conditions"]),
            "load_distance_records": len(payload["load_distance_experiment"]),
            "contact_curves": len(payload["contact_friction_curves"]),
            "image_evidence": len(images),
        },
        "files": {
            "formal_records": FORMAL_RECORDS.relative_to(TEAM_ROOT).as_posix(),
            "image_evidence": FORMAL_IMAGES.relative_to(TEAM_ROOT).as_posix(),
            "parsed_document": PARSED_DOCUMENT.relative_to(CORPUS_ROOT).as_posix(),
            "source_inventory": "source_inventory.json",
        },
        "review": {
            "review_status": "approved_with_documented_source_conflicts",
            "review_date": REVIEW_DATE,
            "scope": "training, RAG evidence and competition demonstration only",
        },
    }
    CURATED_ROOT.mkdir(parents=True, exist_ok=True)
    (CURATED_ROOT / "dataset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _write_markdown(payload: dict[str, Any], images: list[dict[str, Any]]) -> None:
    PARSED_ROOT.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        f"source_id: {SOURCE_ID}",
        f"dataset_id: {DATASET_ID}",
        "domain: tire",
        "source_authority: team_authorized_experiment",
        "authorization_status: authorized",
        "review_status: approved_with_documented_source_conflicts",
        "---",
        "",
        "# 航空轮胎胎面橡胶多接触方式、载荷与温度摩擦磨损实验依据",
        "",
        "本证据集由授权论文、工况表、原始摩擦/温度曲线、磨损与硬度工作簿及显微图交叉整理。完整配方、姓名和学号不进入RAG。",
        "",
        "## 三种接触方式及训练边界",
        "",
        "| 方式 | 载荷/N | 接触应力/MPa | 距离/m | 摩擦副 | 适用训练 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for mode in CONTACT_MODES.values():
        lines.append(
            f"| {mode['name']} | {', '.join(map(str, mode['loads_N']))} | "
            f"{', '.join(map(str, mode['contact_pressures_MPa']))} | {', '.join(map(str, mode['distances_m']))} | "
            f"{mode['counterface']} | {mode['training_scope']} |"
        )
    lines.extend(
        [
            "",
            "## 温度耦合实验",
            "",
            "柱-面接触，50 N、1.5 MPa、120 m、10 mm、3.3 Hz，每组3次。",
            "",
            "| 环境温度/°C | 平均摩擦系数 | 磨损率/g·m⁻¹ | 工作簿硬度/HA | 原始曲线最高界面温度/°C | 证据ID |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for item in payload["temperature_experiment"]["conditions"]:
        lines.append(
            f"| {item['ambient_temperature_C']} | {item['mean_friction_coefficient']:.6f} | "
            f"{item['wear_rate_g_per_m']:.9f} | {item['workbook_reported_hardness_HA']:.4f} | "
            f"{item['maximum_interface_temperature_C']:.1f} | `{item['evidence_id']}` |"
        )
    lines.extend(
        [
            "",
            "## 接触应力与滑动距离",
            "",
            "| 接触应力/MPa | 距离/m | 报告质量损失/g | 报告硬度/HA | 证据ID |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for item in payload["load_distance_experiment"]:
        lines.append(
            f"| {item['contact_pressure_MPa']:.1f} | {item['sliding_distance_m']} | "
            f"{item['reported_wear_loss_g']:.4f} | {item['reported_hardness_HA']:.4f} | `{item['evidence_id']}` |"
        )
    lines.extend(["", "## 经多源复核的机理结论", ""])
    lines.extend(f"- {finding}" for finding in payload["validated_findings"])
    lines.extend(["", "## 图像与图表证据", ""])
    for image in images:
        lines.append(f"- `{image['image_id']}`：{image['condition']}；`{image['relative_path']}`。")
    lines.extend(["", "## 来源差异", ""])
    lines.extend(f"- {conflict}" for conflict in payload["source_conflicts"])
    lines.extend(["", "## 安全边界", "", payload["safety_boundary"], ""])
    PARSED_DOCUMENT.write_text("\n".join(lines), encoding="utf-8")


def _register_source() -> None:
    payload = {"schema_version": "1.0", "sources": []}
    if REGISTRY_PATH.exists():
        payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    entry = {
        "source_id": SOURCE_ID,
        "domain": "tire",
        "title": "航空轮胎胎面橡胶多接触方式、载荷与温度摩擦磨损实验依据",
        "author_or_org": "TEAM-LYQ",
        "document_type": "team_experiment_dataset",
        "license_or_authorization": "authorized",
        "local_file": PARSED_DOCUMENT.relative_to(CORPUS_ROOT).as_posix(),
        "related_files": [
            FORMAL_RECORDS.relative_to(CORPUS_ROOT).as_posix(),
            FORMAL_IMAGES.relative_to(CORPUS_ROOT).as_posix(),
            CURATED_ROOT.relative_to(CORPUS_ROOT).as_posix(),
        ],
        "source_authority": "team_authorized_experiment",
        "acquisition_status": "team_data_approved",
        "checksum": _sha256(FORMAL_RECORDS),
        "notes": "Cross-checked contact-mode, load-distance and temperature evidence with explicit source-conflict handling.",
    }
    sources = [item for item in payload.get("sources", []) if item.get("source_id") != SOURCE_ID]
    sources.append(entry)
    payload["sources"] = sources
    REGISTRY_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


if __name__ == "__main__":
    main()
