from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CORPUS_ROOT = PROJECT_ROOT / "knowledge_corpus"
ASSET_ROOT = CORPUS_ROOT / "experimental_assets"
MEDIA_ROOT = ASSET_ROOT / "media"
REGISTRY_PATH = CORPUS_ROOT / "source_registry.json"
UV_PARSED_PATH = CORPUS_ROOT / "parsed_docs" / "team_tire_rxq_uv_wear_morphology.md"
LOAD_PARSED_PATH = CORPUS_ROOT / "parsed_docs" / "team_tire_lyq_load_distance_matrix.md"
EVAL_PATH = PROJECT_ROOT / "evaluation" / "team_experiment_eval_cases_batch2.json"
LYQ_RECORDS_PATH = (
    CORPUS_ROOT / "raw_docs" / "team_tire" / "data" / "tire_lyq_friction_records.json"
)

UV_SOURCE_ID = "team_tire_rxq_uv_wear_morphology"
LOAD_SOURCE_ID = "team_tire_lyq_load_distance_matrix"
UV_SOURCE_ROOT = Path("H:/\u4efb\u5b5d\u7434/\u7d2b\u5916\u8001\u5316\u540e\u6469\u64e6\u8865\u505a")
LOAD_SOURCE_ROOT = Path("E:/\u6881\u6c38\u7426/\u4e0d\u540c\u8f7d\u8377\u5f80\u590d\u5b9e\u9a8c")

UV_SELECTIONS = [
    (24, "24h/1-1.tif", "wear_track", "1"),
    (24, "24h/2-1.tif", "wear_track", "2"),
    (24, "24h/5.6-1.1.tif", "wear_track", "5.6"),
    (24, "24h/\u78e8\u5c51.tif", "wear_debris", "debris"),
    (504, "504h/1   yumo.tif", "pre_wear_surface", "1"),
    (504, "504h/1-1.tif", "wear_track", "1"),
    (504, "504h/2-1.tif", "wear_track", "2"),
    (504, "504h/5.6-1.tif", "wear_track", "5.6"),
    (576, "576H/1-1.tif", "wear_track", "1"),
    (576, "576H/2-1.tif", "wear_track", "2"),
    (576, "576H/5.6-1.1.tif", "wear_track", "5.6"),
    (576, "576H/5.6-3.1.tif", "wear_track", "5.6"),
]

LOAD_SAMPLE_MAP = {
    40: {20: 2, 40: 4, 80: 6, 120: 8, 160: 10},
    50: {20: 12, 40: 14, 80: 16, 120: 18, 160: 20},
    60: {20: 22, 40: 24, 80: 26, 120: 28, 160: 30},
}


def required_sources() -> list[Path]:
    required = [LYQ_RECORDS_PATH]
    required.extend(UV_SOURCE_ROOT / relative for _, relative, *_ in UV_SELECTIONS)
    for sample_map in LOAD_SAMPLE_MAP.values():
        for sample_number in sample_map.values():
            required.append(_find_load_image(sample_number))
    return required


def build_batch2_assets(
    make_thumbnail: Callable[[Path, Path], None],
    sha256: Callable[[Path], str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    uv_assets = _build_uv_assets(make_thumbnail, sha256)
    load_assets = _build_load_assets(make_thumbnail, sha256)
    return uv_assets, load_assets


def write_batch2_documents(
    uv_assets: list[dict[str, Any]],
    load_assets: list[dict[str, Any]],
    sha256: Callable[[Path], str],
) -> None:
    _write_uv_markdown(uv_assets)
    _write_load_markdown(load_assets)
    _write_batch2_evaluation()
    _register_sources(sha256)


def _build_uv_assets(
    make_thumbnail: Callable[[Path, Path], None],
    sha256: Callable[[Path], str],
) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    target_root = MEDIA_ROOT / "uv_aging_wear"
    target_root.mkdir(parents=True, exist_ok=True)
    sequence_by_duration: dict[int, int] = defaultdict(int)
    for duration_h, relative, image_role, scale_label in UV_SELECTIONS:
        sequence_by_duration[duration_h] += 1
        sequence = sequence_by_duration[duration_h]
        source = UV_SOURCE_ROOT / relative
        asset_id = f"RXQ-UV-H{duration_h:04d}-IMG-{sequence:02d}"
        target = target_root / f"{asset_id}.jpg"
        make_thumbnail(source, target)
        role_title = {
            "wear_track": "摩擦磨损形貌",
            "wear_debris": "磨屑形貌",
            "pre_wear_surface": "摩擦前表面形貌",
        }[image_role]
        assets.append(
            {
                "asset_id": asset_id,
                "experiment_id": "TIRE-RXQ-UV-WEAR-001",
                "sample_id": f"RXQ-UV-{duration_h:04d}H-{sequence:02d}",
                "domain": "tire",
                "topic": "uv_aging_wear_morphology",
                "title": f"紫外老化 {duration_h} h 后{role_title}",
                "modality": "optical_image",
                "media_type": "image/jpeg",
                "media_path": target.relative_to(ASSET_ROOT).as_posix(),
                "source_reference": f"授权团队实验资料/RXQ/紫外老化后摩擦补做/{relative}",
                "source_sha256": sha256(source),
                "derived_sha256": sha256(target),
                "condition": {
                    "uv_source": "UVA-340",
                    "wavelength_range_nm": "295-365",
                    "irradiance_W_m2": 0.6,
                    "aging_duration_h": duration_h,
                    "image_role": image_role,
                    "nominal_scale_label_from_filename": scale_label,
                    "friction_condition_status": "pending_source_confirmation",
                },
                "labels": ["紫外老化", role_title, f"{duration_h}h"],
                "severity": "training_unrated",
                "observation": "该资产保留老化时长和图像角色，用于跨时长形貌描述训练。",
                "training_use": "先描述可见形貌，再结合老化时长提出机理假设和所需补充证据。",
                "review_status": "reviewed",
                "authorization_status": "authorized",
                "linked_source_ids": [UV_SOURCE_ID, "team_tire_rxq_aging_multimodal_evidence"],
                "linked_evidence_ids": [f"RXQ-UV-WEAR-{duration_h:04d}H"],
                "limitations": "当前图像目录未提供可唯一核对的摩擦载荷、速度和行程；文件名中的数值只作为图像标签，不解释为已确认放大倍数。",
            }
        )
    return assets


def _build_load_assets(
    make_thumbnail: Callable[[Path, Path], None],
    sha256: Callable[[Path], str],
) -> list[dict[str, Any]]:
    payload = json.loads(LYQ_RECORDS_PATH.read_text(encoding="utf-8"))
    records = payload["load_distance_experiment"]
    target_root = MEDIA_ROOT / "load_distance_matrix"
    target_root.mkdir(parents=True, exist_ok=True)
    assets: list[dict[str, Any]] = []

    chart_path = target_root / "LYQ-LOAD-MATRIX-TREND-01.png"
    _draw_load_matrix_chart(records, chart_path)
    assets.append(
        {
            "asset_id": "LYQ-LOAD-MATRIX-TREND-01",
            "experiment_id": "TIRE-EXP-LYQ-FRICTION-001",
            "sample_id": "LYQ-LOAD-MATRIX-SUMMARY",
            "domain": "tire",
            "topic": "load_distance_morphology_matrix",
            "title": "不同载荷与滑动距离下磨损量及硬度趋势",
            "modality": "derived_curve",
            "media_type": "image/png",
            "media_path": chart_path.relative_to(ASSET_ROOT).as_posix(),
            "source_reference": "授权团队实验资料/LYQ/tire_lyq_friction_records.json",
            "source_sha256": sha256(LYQ_RECORDS_PATH),
            "derived_sha256": sha256(chart_path),
            "condition": {
                "loads_N": [40, 50, 60],
                "distances_m": [20, 40, 80, 120, 160],
                "contact_mode": "cylinder_flat",
                "temperature_evidence_coverage": "partial_by_load_group",
            },
            "labels": ["载荷-距离矩阵", "磨损量", "硬度", "部分温升证据"],
            "severity": "not_applicable",
            "observation": "图中汇总 15 个已核对工况，用于比较载荷和滑动距离对磨损量、硬度的共同影响。",
            "training_use": "识别趋势、异常点和交互效应，并将结论限定在已测工况范围内。",
            "review_status": "reviewed",
            "authorization_status": "authorized",
            "linked_source_ids": [LOAD_SOURCE_ID, "team_tire_lyq_contact_load_temperature_evidence"],
            "linked_evidence_ids": [item["evidence_id"] for item in records],
            "limitations": "温升原始记录未覆盖每个载荷-距离单元；本图不生成或插补单元级温升数值。",
        }
    )

    for record in records:
        load = int(record["load_N"])
        distance = int(record["sliding_distance_m"])
        sample_number = LOAD_SAMPLE_MAP[load][distance]
        source = _find_load_image(sample_number)
        asset_id = f"LYQ-LOAD-L{load:02d}-D{distance:03d}-OPT-01"
        target = target_root / f"{asset_id}.jpg"
        make_thumbnail(source, target)
        assets.append(
            {
                "asset_id": asset_id,
                "experiment_id": "TIRE-EXP-LYQ-FRICTION-001",
                "sample_id": f"LYQ-RECIP-{sample_number:02d}",
                "domain": "tire",
                "topic": "load_distance_morphology_matrix",
                "title": f"{load} N、{distance} m 往复摩擦光学形貌",
                "modality": "optical_image",
                "media_type": "image/jpeg",
                "media_path": target.relative_to(ASSET_ROOT).as_posix(),
                "source_reference": f"授权团队实验资料/LYQ/不同载荷往复实验/{source.relative_to(LOAD_SOURCE_ROOT).as_posix()}",
                "source_sha256": sha256(source),
                "derived_sha256": sha256(target),
                "condition": {
                    "contact_mode": record["contact_mode"],
                    "normal_load_N": load,
                    "contact_pressure_MPa": record["contact_pressure_MPa"],
                    "sliding_distance_m": distance,
                    "stroke_mm": record["stroke_mm"],
                    "frequency_Hz": record["frequency_Hz"],
                    "reported_wear_loss_g": record["reported_wear_loss_g"],
                    "reported_hardness_HA": record["reported_hardness_HA"],
                    "nominal_scale_label_from_filename": "2",
                    "temperature_evidence_status": "not_available_for_this_matrix_cell",
                },
                "labels": ["往复摩擦", f"{load}N", f"{distance}m", "磨损形貌"],
                "severity": "training_unrated",
                "observation": "该图像与载荷、接触压力、距离、磨损量和硬度记录绑定。",
                "training_use": "在同载荷或同距离条件下比较形貌，并用定量记录验证趋势判断。",
                "review_status": "reviewed",
                "authorization_status": "authorized",
                "linked_source_ids": [LOAD_SOURCE_ID, "team_tire_lyq_contact_load_temperature_evidence"],
                "linked_evidence_ids": [record["evidence_id"]],
                "limitations": "采用每个矩阵单元的一张代表性光学图像；代表视野不能替代多视野统计，温升证据不可从图像反推。",
            }
        )
    return assets


def _find_load_image(sample_number: int) -> Path:
    matches = list((LOAD_SOURCE_ROOT / "\u5149\u5b66\u663e\u5fae\u955c").rglob(f"{sample_number} 2.tif"))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"expected one optical image for sample {sample_number}, found {len(matches)}"
        )
    return matches[0]


def _draw_load_matrix_chart(records: list[dict[str, Any]], target: Path) -> None:
    width, height = 1200, 760
    image = Image.new("RGB", (width, height), "#f7faf9")
    draw = ImageDraw.Draw(image)
    draw.text((55, 25), "Reciprocating friction: load x distance evidence matrix", fill="#15272b")
    colors = {40: "#176b63", 50: "#b95840", 60: "#315b79"}
    for panel_index, (field, label) in enumerate(
        [("reported_wear_loss_g", "Wear loss (g)"), ("reported_hardness_HA", "Hardness (HA)")]
    ):
        left, top, right, bottom = 90, 115 + panel_index * 300, 1130, 330 + panel_index * 300
        draw.line((left, top, left, bottom), fill="#87989b", width=2)
        draw.line((left, bottom, right, bottom), fill="#87989b", width=2)
        draw.text((left, top - 30), label, fill="#263a3f")
        values = [float(item[field]) for item in records]
        low, high = min(values), max(values)
        span = high - low or 1.0
        for load in (40, 50, 60):
            rows = sorted(
                (item for item in records if int(item["load_N"]) == load),
                key=lambda item: item["sliding_distance_m"],
            )
            points = []
            for index, row in enumerate(rows):
                x = left + index * (right - left) / 4
                value = float(row[field])
                y = bottom - 18 - (value - low) / span * (bottom - top - 36)
                points.append((x, y))
                draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=colors[load])
                if panel_index == 1:
                    draw.text((x - 12, bottom + 9), str(row["sliding_distance_m"]), fill="#4a5e62")
            draw.line(points, fill=colors[load], width=4)
            draw.text((right - 235 + (load - 40) * 6, top - 30), f"{load} N", fill=colors[load])
    draw.text((90, 710), "Sliding distance (m). Temperature evidence is partial and is not interpolated.", fill="#4a5e62")
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, format="PNG", optimize=True)


def _write_uv_markdown(assets: list[dict[str, Any]]) -> None:
    lines = [
        "---",
        f"source_id: {UV_SOURCE_ID}",
        "domain: tire",
        "source_authority: team_authorized_experiment",
        "authorization_status: authorized",
        "review_status: reviewed",
        "---",
        "",
        "# 航空轮胎胎面橡胶紫外老化后摩擦形貌证据",
        "",
        "本专题整理 UVA-340 紫外老化 24 h、504 h 和 576 h 后的代表性光学形貌。已确认波长范围为 295-365 nm、辐照度为 0.6 W/m²；当前图像目录无法唯一确认摩擦载荷、速度和行程，因此这些参数不进入确定性结论。",
        "",
        "## 证据资产",
        "",
        "| 老化时长 | 图像角色 | 文件标签 | 资产 ID |",
        "| --- | --- | --- | --- |",
    ]
    for asset in assets:
        condition = asset["condition"]
        lines.append(
            f"| {condition['aging_duration_h']} h | {condition['image_role']} | "
            f"{condition['nominal_scale_label_from_filename']} | `{asset['asset_id']}` |"
        )
    lines.extend(
        [
            "",
            "## 训练与审核边界",
            "",
            "1. 先按裂纹、沟槽、剥落、磨屑和表面粗糙化等可见事实描述，不从单图直接判定机理。",
            "2. 跨时长比较时保持图像角色和尺度标签一致；不把亮度差异直接解释为老化程度。",
            "3. 机理结论须与拉伸、硬度、FTIR 或已确认摩擦工况交叉验证。",
            "4. 若摩擦参数未补齐，审核 Agent 应输出证据不足并要求补录，而不是生成确定性因果结论。",
            "",
        ]
    )
    UV_PARSED_PATH.write_text("\n".join(lines), encoding="utf-8")


def _write_load_markdown(assets: list[dict[str, Any]]) -> None:
    image_assets = [item for item in assets if item["modality"] == "optical_image"]
    lines = [
        "---",
        f"source_id: {LOAD_SOURCE_ID}",
        "domain: tire",
        "source_authority: team_authorized_experiment",
        "authorization_status: authorized",
        "review_status: reviewed",
        "---",
        "",
        "# 不同载荷往复摩擦的载荷-距离-形貌训练矩阵",
        "",
        "本专题绑定圆柱-平面往复摩擦的 3 个载荷、5 个滑动距离、15 个定量记录与代表性光学形貌。试验行程 10 mm、频率 3.3 Hz。温升资料目前只能作为部分载荷组的辅助证据，不能插补为 15 个单元的温升矩阵。",
        "",
        "## 十五个工况单元",
        "",
        "| 载荷 | 接触压力 | 距离 | 磨损量 | 硬度 | 图像资产 | 证据 ID |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for asset in image_assets:
        c = asset["condition"]
        lines.append(
            f"| {c['normal_load_N']} N | {c['contact_pressure_MPa']} MPa | {c['sliding_distance_m']} m | "
            f"{c['reported_wear_loss_g']:.4f} g | {c['reported_hardness_HA']:.4f} HA | "
            f"`{asset['asset_id']}` | `{asset['linked_evidence_ids'][0]}` |"
        )
    lines.extend(
        [
            "",
            "## 训练与审核边界",
            "",
            "- 同载荷比较距离效应，同距离比较载荷效应，避免混合变量后直接归因。",
            "- 形貌观察必须与磨损量和硬度记录交叉验证，代表图不能替代重复试验统计。",
            "- 温升证据状态应显式显示为 partial；没有单元记录时不得生成温度数值。",
            "- 所有趋势只适用于已测载荷、接触形式、距离和环境范围。",
            "",
        ]
    )
    LOAD_PARSED_PATH.write_text("\n".join(lines), encoding="utf-8")


def _register_sources(sha256: Callable[[Path], str]) -> None:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    entries = [
        {
            "source_id": UV_SOURCE_ID,
            "domain": "tire",
            "title": "航空轮胎胎面橡胶紫外老化后摩擦形貌证据",
            "author_or_org": "TEAM-RXQ",
            "document_type": "team_experiment_image_dataset",
            "license_or_authorization": "authorized",
            "local_file": UV_PARSED_PATH.relative_to(CORPUS_ROOT).as_posix(),
            "related_files": ["experimental_assets/catalog.json"],
            "source_authority": "team_authorized_experiment",
            "acquisition_status": "team_data_approved_with_condition_limit",
            "checksum": sha256(UV_PARSED_PATH),
            "notes": "Twelve reviewed image assets; friction parameters remain explicitly pending confirmation.",
        },
        {
            "source_id": LOAD_SOURCE_ID,
            "domain": "tire",
            "title": "不同载荷往复摩擦的载荷-距离-形貌训练矩阵",
            "author_or_org": "TEAM-LYQ",
            "document_type": "team_experiment_matrix_dataset",
            "license_or_authorization": "authorized",
            "local_file": LOAD_PARSED_PATH.relative_to(CORPUS_ROOT).as_posix(),
            "related_files": [
                "raw_docs/team_tire/data/tire_lyq_friction_records.json",
                "experimental_assets/catalog.json",
            ],
            "source_authority": "team_authorized_experiment",
            "acquisition_status": "team_data_approved",
            "checksum": sha256(LOAD_PARSED_PATH),
            "notes": "Fifteen load-distance morphology cells plus one derived trend chart; temperature coverage is partial.",
        },
    ]
    replace_ids = {entry["source_id"] for entry in entries}
    sources = [item for item in payload.get("sources", []) if item.get("source_id") not in replace_ids]
    sources.extend(entries)
    payload["sources"] = sources
    REGISTRY_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_batch2_evaluation() -> None:
    agent_steps = [
        "DiagnosisAgent",
        "MaterialRouterAgent",
        "RetrievalAgent",
        "GenerationAgent",
        "ReviewAgent",
        "DecisionAgent",
    ]
    specs = [
        ("b2-uv-ret-001", "知识检索测试", "检索24小时紫外老化后的摩擦磨损形貌", ["24h", "紫外老化", "摩擦形貌"], ["RXQ-UV-H0024-IMG-01"], "继续巩固", "返回24小时资产、来源和工况限制"),
        ("b2-uv-ret-002", "知识检索测试", "比较504小时紫外老化的摩擦前与摩擦后表面", ["504h", "摩擦前", "摩擦后"], ["RXQ-UV-H0504-IMG-01", "RXQ-UV-H0504-IMG-02"], "补充案例", "同时返回摩擦前和摩擦后资产"),
        ("b2-uv-ret-003", "知识检索测试", "查看576小时紫外老化后的不同视野形貌", ["576h", "代表视野", "尺度标签"], ["RXQ-UV-H0576-IMG-01", "RXQ-UV-H0576-IMG-03"], "继续巩固", "返回同一时长多个代表视野"),
        ("b2-uv-ret-004", "知识检索测试", "紫外老化后磨屑证据有哪些", ["磨屑", "24h", "证据ID"], ["RXQ-UV-H0024-IMG-04"], "补充案例", "命中磨屑资产并显示证据ID"),
        ("b2-uv-img-001", "个性化资源生成测试", "比较24、504、576小时紫外老化后表面形貌", ["变量控制", "可见事实", "跨时长"], ["RXQ-UV-H0024-IMG-01", "RXQ-UV-H0504-IMG-02", "RXQ-UV-H0576-IMG-01"], "补充案例", "讲义区分观察事实与机理假设"),
        ("b2-uv-img-002", "审核纠偏测试", "根据单张504小时图像确定紫外老化导致裂纹的完整机理", ["单图不足", "交叉表征", "降级输出"], ["RXQ-UV-H0504-IMG-02"], "继续巩固", "审核Agent拒绝无依据的确定性机理"),
        ("b2-uv-img-003", "审核纠偏测试", "把文件名5.6解释为已确认的显微镜放大倍数", ["文件名标签", "参数待核", "不可推断"], ["RXQ-UV-H0576-IMG-03"], "降维解释", "明确5.6仅为文件标签"),
        ("b2-uv-img-004", "反馈迭代测试", "学习者把图像亮度直接当作老化程度", ["亮度误区", "同尺度比较", "补充表征"], ["RXQ-UV-H0024-IMG-01", "RXQ-UV-H0504-IMG-02"], "继续巩固", "反馈指出亮度不能单独表征老化"),
        ("b2-load-ret-001", "知识检索测试", "检索40N下20到160米往复摩擦矩阵", ["40N", "五个距离", "光学形貌"], ["LYQ-LOAD-L40-D020-OPT-01", "LYQ-LOAD-L40-D160-OPT-01"], "继续巩固", "命中40N距离序列"),
        ("b2-load-ret-002", "知识检索测试", "比较80米时40、50、60N磨损", ["80m", "载荷效应", "磨损量"], ["LYQ-LOAD-L40-D080-OPT-01", "LYQ-LOAD-L50-D080-OPT-01", "LYQ-LOAD-L60-D080-OPT-01"], "进阶挑战", "同距离比较三个载荷"),
        ("b2-load-ret-003", "知识检索测试", "载荷距离矩阵的磨损量和硬度趋势", ["趋势图", "磨损量", "硬度"], ["LYQ-LOAD-MATRIX-TREND-01"], "进阶挑战", "返回趋势图和15个工况范围"),
        ("b2-load-ret-004", "知识检索测试", "检索60N 160米的工况和形貌", ["60N", "160m", "1.8MPa"], ["LYQ-LOAD-L60-D160-OPT-01"], "补充案例", "工况字段与记录一致"),
        ("b2-load-gen-001", "个性化资源生成测试", "为本科生生成载荷距离变量控制实操指南", ["控制变量", "同载荷", "同距离"], ["LYQ-LOAD-MATRIX-TREND-01"], "继续巩固", "指南包含两种单变量比较路径"),
        ("b2-load-gen-002", "个性化资源生成测试", "为研究生分析60N下距离增加时磨损和硬度变化", ["60N", "定量记录", "形貌验证"], ["LYQ-LOAD-L60-D020-OPT-01", "LYQ-LOAD-L60-D160-OPT-01"], "进阶挑战", "引用端点数值并说明外推边界"),
        ("b2-load-gen-003", "个性化资源生成测试", "生成载荷和距离交互效应的案例任务", ["二维矩阵", "交互效应", "重复试验"], ["LYQ-LOAD-MATRIX-TREND-01"], "进阶挑战", "任务要求定量与形貌交叉验证"),
        ("b2-load-gen-004", "反馈迭代测试", "学习者混合不同载荷和距离后直接归因", ["混杂变量", "分组比较", "纠偏"], ["LYQ-LOAD-MATRIX-TREND-01"], "降维解释", "反馈要求固定一个变量后再比较"),
        ("b2-review-001", "审核纠偏测试", "为15个工况补齐没有记录的温升数值", ["禁止插补", "部分温升证据", "证据不足"], ["LYQ-LOAD-MATRIX-TREND-01"], "继续巩固", "审核Agent拒绝编造温升"),
        ("b2-review-002", "审核纠偏测试", "仅凭50 N、80 m的一张代表图判断整个样品磨损分布", ["代表视野", "多视野统计", "限制"], ["LYQ-LOAD-L50-D080-OPT-01"], "补充案例", "输出代表视野限制和复检建议"),
        ("b2-feedback-001", "反馈迭代测试", "测试正确率40%，且混淆磨损量与磨损率", ["指标区分", "降维解释", "单位"], ["LYQ-LOAD-MATRIX-TREND-01"], "降维解释", "决策Agent输出降维解释"),
        ("b2-feedback-002", "反馈迭代测试", "测试正确率85%，能比较80 m下40 N与60 N并完成证据引用", ["较高正确率", "巩固训练", "证据引用"], ["LYQ-LOAD-L40-D080-OPT-01", "LYQ-LOAD-L60-D080-OPT-01"], "继续巩固", "决策Agent按90%阈值前继续巩固"),
    ]
    cases = []
    for case_id, test_type, input_text, key_points, asset_ids, action, criteria in specs:
        cases.append(
            {
                "id": case_id,
                "test_type": test_type,
                "learner_profile": "材料方向研究生" if "gen-002" in case_id else "本科低年级学生",
                "domain": "tire",
                "input": input_text,
                "expected_key_points": key_points,
                "expected_asset_ids": asset_ids,
                "expected_agent_steps": agent_steps,
                "expected_next_action": action,
                "pass_criteria": criteria,
            }
        )
    payload = {
        "schema_version": "1.0",
        "dataset": "team_experiment_batch2_evaluation",
        "description": "紫外老化摩擦形貌与载荷-距离-形貌矩阵专项测评集。",
        "cases": cases,
    }
    EVAL_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
