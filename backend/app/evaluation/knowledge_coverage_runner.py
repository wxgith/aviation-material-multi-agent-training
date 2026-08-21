from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CORPUS_ROOT = PROJECT_ROOT / "knowledge_corpus"
MANIFEST_PATH = CORPUS_ROOT / "index_manifest.json"
REGISTRY_PATH = CORPUS_ROOT / "source_registry.json"
RESULTS_PATH = PROJECT_ROOT / "evaluation" / "knowledge_coverage_results.json"
SUMMARY_PATH = PROJECT_ROOT / "evaluation" / "knowledge_coverage_summary.md"

DOMAIN_NAMES = {
    "tire": "航空轮胎",
    "brake": "航空刹车",
    "composite": "复合材料",
}

CATEGORY_RULES = {
    "tire": {
        "材料与基础概念": ["橡胶", "胎面", "交联", "材料"],
        "热氧与紫外老化": ["热氧", "紫外", "老化", "氧化"],
        "摩擦磨损": ["摩擦", "磨损", "滑动", "制动"],
        "裂纹与剥落": ["裂纹", "疲劳", "剥落", "撕裂"],
        "实验工况": ["载荷", "距离", "温度", "速度", "实验", "试验", "工况"],
        "表征与图像": ["形貌", "显微", "sem", "表征", "图像"],
        "检查与维护判读": ["维护", "检查", "判读", "风险", "起降", "放行"],
        "实操训练": ["实操", "任务", "训练", "指南"],
    },
    "brake": {
        "结构与基础概念": ["刹车", "制动", "碳", "结构", "brake"],
        "高温摩擦": ["高温", "摩擦", "温升", "thermal", "friction"],
        "磨损与形貌": ["磨损", "形貌", "沟槽", "磨屑", "wear"],
        "氧化与裂纹": ["氧化", "裂纹", "热应力", "oxidation", "crack"],
        "性能与热衰退": ["热衰退", "摩擦系数", "性能", "fade"],
        "试验工况": ["能量", "压力", "速度", "温度", "试验", "实验", "工况"],
        "检查与维护": ["检查", "维护", "磨损指示", "放气", "泄漏", "inspection", "service"],
        "失效机理": ["失效", "机理", "证据链", "risk"],
    },
    "composite": {
        "结构与基础概念": ["复合材料", "层合", "基体", "纤维", "sandwich"],
        "冲击与BVID": ["冲击", "bvid", "impact", "凹坑"],
        "分层/基体/纤维损伤": ["分层", "基体开裂", "纤维断裂", "delamination", "matrix", "fiber"],
        "无损检测": ["无损", "超声", "c扫", "c-scan", "ct", "敲击", "热成像", "ultrasonic"],
        "扩展与损伤容限": ["扩展", "损伤容限", "残余强度", "疲劳", "propagation"],
        "图像判读": ["图像", "成像", "重建", "判读", "image", "scan"],
        "检查与维修边界": ["检查", "维修", "修理", "维护", "放行", "inspection", "repair"],
        "冲击试验工况": ["落锤", "能量", "冲击器", "试验", "实验", "astm", "layup"],
    },
}

AUTHORITATIVE = {"official_primary", "peer_reviewed_open_access", "peer_reviewed_open_dataset"}
EXPERIMENTAL = {
    "team_authorized_experiment",
    "peer_reviewed_open_dataset",
    "open_dataset",
    "peer_reviewed_open_access",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _category_metrics(
    chunks: list[dict[str, Any]],
    rules: dict[str, list[str]],
    registry_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    results = []
    for category, keywords in rules.items():
        hits = []
        for chunk in chunks:
            source = registry_by_id.get(chunk.get("source_id", ""), {})
            haystack = " ".join(
                [
                    chunk.get("title", ""),
                    *[str(tag) for tag in chunk.get("tags", [])],
                    source.get("title", ""),
                    source.get("document_type", ""),
                    *[str(section) for section in source.get("applicable_sections", [])],
                ]
            ).lower()
            if any(keyword.lower() in haystack for keyword in keywords):
                hits.append(chunk)
        sources = sorted({item.get("source_id", "") for item in hits if item.get("source_id")})
        if len(hits) >= 5 and len(sources) >= 2:
            status = "strong"
        elif len(hits) >= 2 and sources:
            status = "adequate"
        elif hits:
            status = "weak"
        else:
            status = "missing"
        results.append(
            {
                "category": category,
                "status": status,
                "chunk_count": len(hits),
                "source_count": len(sources),
                "sample_evidence_ids": [item["id"] for item in hits[:5]],
            }
        )
    return results


def analyze_coverage() -> dict[str, Any]:
    manifest = _load_json(MANIFEST_PATH)
    registry = _load_json(REGISTRY_PATH)
    registry_by_id = {item["source_id"]: item for item in registry.get("sources", [])}
    chunks_by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for chunk in manifest.get("chunks", []):
        if chunk.get("domain") in DOMAIN_NAMES:
            chunks_by_domain[chunk["domain"]].append(chunk)

    domains = {}
    for domain, label in DOMAIN_NAMES.items():
        chunks = chunks_by_domain[domain]
        source_ids = {item.get("source_id", "") for item in chunks if item.get("source_id")}
        authority_counts = Counter(item.get("source_authority", "unknown") for item in chunks)
        categories = _category_metrics(chunks, CATEGORY_RULES[domain], registry_by_id)
        category_score = sum(
            {"strong": 1.0, "adequate": 0.75, "weak": 0.35, "missing": 0.0}[item["status"]]
            for item in categories
        ) / len(categories)
        authoritative_sources = {
            source_id
            for source_id in source_ids
            if registry_by_id.get(source_id, {}).get("source_authority") in AUTHORITATIVE
            or next(
                (
                    item.get("source_authority")
                    for item in chunks
                    if item.get("source_id") == source_id
                ),
                "",
            )
            in AUTHORITATIVE
        }
        experimental_sources = {
            source_id
            for source_id in source_ids
            if registry_by_id.get(source_id, {}).get("source_authority") in EXPERIMENTAL
            or next(
                (
                    item.get("source_authority")
                    for item in chunks
                    if item.get("source_id") == source_id
                ),
                "",
            )
            in EXPERIMENTAL
        }
        team_sources = {
            source_id
            for source_id in source_ids
            if registry_by_id.get(source_id, {}).get("source_authority")
            == "team_authorized_experiment"
        }
        authority_score = min(len(authoritative_sources) / 4, 1.0)
        experiment_score = min(len(experimental_sources) / 3, 1.0)
        score = round((category_score * 0.7 + authority_score * 0.15 + experiment_score * 0.15) * 100, 1)
        priorities = []
        for item in categories:
            if item["status"] in {"missing", "weak"}:
                priorities.append(f"补充“{item['category']}”的独立来源与可定位证据")
        if not team_sources:
            priorities.append("补充授权实验记录、工况参数、图像及专家判读样例")
        domains[domain] = {
            "label": label,
            "inventory_score": score,
            "chunk_count": len(chunks),
            "source_count": len(source_ids),
            "authoritative_source_count": len(authoritative_sources),
            "experimental_source_count": len(experimental_sources),
            "team_experiment_source_count": len(team_sources),
            "authority_chunk_counts": dict(authority_counts),
            "categories": categories,
            "priorities": priorities,
        }

    pending_sources = [
        {
            "source_id": item["source_id"],
            "domain": item.get("domain", ""),
            "title": item.get("title", ""),
            "status": item.get("acquisition_status", ""),
        }
        for item in registry.get("sources", [])
        if item.get("acquisition_status")
        not in {
            "downloaded_and_checksum_verified",
            "team_data_approved",
            "team_data_approved_with_condition_limit",
        }
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "inventory coverage proxy based on title/tag/source metadata; not a professional accuracy score",
        "total_chunks": manifest.get("total_chunks", len(manifest.get("chunks", []))),
        "registered_sources": len(registry.get("sources", [])),
        "domains": domains,
        "pending_sources": pending_sources,
    }


def render_summary(payload: dict[str, Any]) -> str:
    rows = [
        "# 三领域知识覆盖差距分析",
        "",
        f"生成时间：`{payload['generated_at']}`",
        "",
        "> 本报告是基于标题、标签、来源类型和证据数量的库存覆盖代理分析，不等同于专业正确率或课程完整度评价。",
        "",
        "| 领域 | 切片 | 独立来源 | 权威来源 | 实验来源 | 团队实验 | 库存覆盖分 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in payload["domains"].values():
        rows.append(
            f"| {item['label']} | {item['chunk_count']} | {item['source_count']} | "
            f"{item['authoritative_source_count']} | {item['experimental_source_count']} | "
            f"{item['team_experiment_source_count']} | {item['inventory_score']} |"
        )
    for domain, item in payload["domains"].items():
        rows.extend(
            [
                "",
                f"## {item['label']}",
                "",
                "| 能力维度 | 状态 | 切片 | 来源 | 代表证据 |",
                "| --- | --- | ---: | ---: | --- |",
            ]
        )
        for category in item["categories"]:
            rows.append(
                f"| {category['category']} | {category['status']} | {category['chunk_count']} | "
                f"{category['source_count']} | {', '.join(category['sample_evidence_ids']) or '-'} |"
            )
        rows.extend(["", "优先补强："])
        rows.extend(f"- {priority}" for priority in item["priorities"] or ["维持现有覆盖并做专家抽样复核"])
    rows.extend(["", "## 待获取或待核对来源", ""])
    if payload["pending_sources"]:
        rows.extend(
            f"- `{item['source_id']}`（{item['domain']}）：{item['title']}，状态：{item['status']}"
            for item in payload["pending_sources"]
        )
    else:
        rows.append("- 无。")
    return "\n".join(rows) + "\n"


def run() -> dict[str, Any]:
    payload = analyze_coverage()
    RESULTS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SUMMARY_PATH.write_text(render_summary(payload), encoding="utf-8")
    return payload


def main() -> None:
    payload = run()
    print(
        json.dumps(
            {
                "total_chunks": payload["total_chunks"],
                "scores": {
                    key: value["inventory_score"] for key, value in payload["domains"].items()
                },
                "summary": str(SUMMARY_PATH.relative_to(PROJECT_ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
