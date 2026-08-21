from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ChunkingConfig:
    domain: str
    source_id: str
    title_prefix: str
    source_url: str = ""
    source_authority: str = "curated_local"
    max_chars: int = 700
    overlap: int = 80


def chunk_markdown(markdown_text: str, config: ChunkingConfig) -> list[dict]:
    """Split Markdown by headings/paragraphs and then by fixed length."""
    sections = _split_sections(_strip_frontmatter(markdown_text))
    chunks: list[dict] = []
    counter = 1
    for heading, body in sections:
        text = _clean_text(body)
        if not text:
            continue
        for part in _window_text(text, config.max_chars, config.overlap):
            chunk_id = _chunk_id(config.source_id, counter, part)
            chunks.append(
                {
                    "id": chunk_id,
                    "domain": config.domain,
                    "title": (
                        f"{config.title_prefix} · {heading}"
                        if heading
                        else f"{config.title_prefix}-{counter}"
                    ),
                    "tags": _infer_tags(heading, part, config.domain),
                    "difficulty": _infer_difficulty(part),
                    "content": part,
                    "source_type": "parsed_markdown",
                    "source_id": config.source_id,
                    "source_locator": heading or f"chunk-{counter}",
                    "source_url": config.source_url,
                    "source_authority": config.source_authority,
                    "applicable_learners": ["本科低年级学生", "材料方向研究生", "机务维修新员工"],
                    "common_misconceptions": [],
                }
            )
            counter += 1
    return chunks


def _strip_frontmatter(markdown_text: str) -> str:
    if not markdown_text.startswith("---"):
        return markdown_text
    match = re.match(r"^---\s*\n.*?\n---\s*\n", markdown_text, flags=re.DOTALL)
    return markdown_text[match.end():] if match else markdown_text


def chunk_markdown_file(path: Path, config: ChunkingConfig) -> list[dict]:
    return chunk_markdown(path.read_text(encoding="utf-8"), config)


def _split_sections(markdown_text: str) -> list[tuple[str, str]]:
    current_heading = ""
    current_lines: list[str] = []
    sections: list[tuple[str, str]] = []
    for line in markdown_text.splitlines():
        match = re.match(r"^(#{1,4})\s+(.+)$", line.strip())
        if match:
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines)))
                current_lines = []
            current_heading = match.group(2).strip()
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_heading, "\n".join(current_lines)))
    return sections


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _window_text(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


def _chunk_id(source_id: str, counter: int, content: str) -> str:
    digest = hashlib.sha1(content.encode("utf-8")).hexdigest()[:8]
    safe_source = re.sub(r"[^a-zA-Z0-9_-]+", "-", source_id).strip("-")
    return f"{safe_source}-c{counter:03d}-{digest}"


def _infer_tags(heading: str, content: str, domain: str) -> list[str]:
    candidates = [
        "热氧老化", "滑动磨损", "胎面裂纹", "剥落", "高温摩擦", "热衰退",
        "氧化", "裂纹", "冲击损伤", "分层", "无损检测", "损伤扩展",
        "实操训练", "审核纠偏", "事故案例", "维护决策", "轮胎欠压",
    ]
    source = f"{heading} {content}"
    tags = [item for item in candidates if item in source]
    lowered = source.lower()
    bilingual_rules = {
        "tire": [
            (("tire", "tread"), ["航空轮胎", "损伤等级判读"]),
            (("crack",), ["胎面裂纹", "损伤等级判读"]),
            (("wear", "worn", "abrasion"), ["滑动磨损", "磨损形貌"]),
            (("fatigue",), ["疲劳磨损", "损伤机理"]),
            (("oxidation", "thermo-oxid", "thermal aging"), ["热氧老化", "损伤机理"]),
            (("slip angle", "sliding"), ["滑动磨损", "实验表征"]),
            (("slip ratio", "runway surface"), ["滑动磨损", "跑道工况", "实验表征"]),
            (("underinflation", "underinflated", "tire pressure"), ["轮胎欠压", "维护决策", "损伤等级判读"]),
            (("accident", "probable cause", "rejected takeoff"), ["事故案例", "维护决策"]),
            (("inspection", "maintenance"), ["损伤等级判读", "实操训练"]),
        ],
        "brake": [
            (("wear", "worn"), ["磨损形貌", "失效机理"]),
            (("oxidation", "oxide"), ["氧化", "失效机理", "热衰退"]),
            (("surface crack", "crack growth"), ["裂纹", "失效机理"]),
            (("temperature", "thermal", "heating"), ["高温摩擦", "热衰退", "失效机理"]),
            (("friction", "sliding"), ["高温摩擦", "磨损形貌", "热衰退"]),
            (("wear pin", "maintenance", "fleet"), ["维护决策", "实操训练"]),
            (("inspection", "brake lining", "brake disk", "brake assembly"), ["刹车检查", "实操训练", "维护决策"]),
            (("wear indicator", "wear pin", "minimum lining"), ["刹车衬片", "刹车检查", "维护决策"]),
            (("brake bleeding", "pressure bleed", "bleed port"), ["刹车放气", "实操训练", "维护决策"]),
            (("overheating", "aborted takeoff", "rejected takeoff"), ["刹车过热", "刹车检查", "维护决策"]),
            (("antiskid", "hydraulic pressure"), ["制动系统", "实操训练"]),
        ],
        "composite": [
            (("impact damage", "drop-weight impact", "low velocity impact"), ["冲击损伤", "损伤扩展"]),
            (("delamination", "disbond"), ["分层", "损伤扩展"]),
            (("matrix crack", "transverse crack"), ["基体开裂", "冲击损伤"]),
            (("fiber failure", "fiber breakage"), ["纤维断裂", "损伤扩展"]),
            (("ultrasonic", "c-scan", "phased array", "thermography", "x-ray", "nondestructive"), ["无损检测", "无损检测图像判读"]),
            (("shearography",), ["无损检测", "剪切散斑检测", "无损检测图像判读"]),
            (("residual strength", "compression after impact"), ["冲击后剩余强度", "损伤扩展"]),
            (("inspection", "detectability"), ["无损检测图像判读", "损伤等级判读"]),
            (("coin tap", "tap test", "audible sonic"), ["敲击检测", "分层", "无损检测"]),
            (("pulse echo", "through transmission", "bond tester"), ["超声检测", "分层", "无损检测图像判读"]),
        ],
    }
    for keywords, inferred_tags in bilingual_rules.get(domain, []):
        if any(keyword in lowered for keyword in keywords):
            tags.extend(inferred_tags)
    return list(dict.fromkeys(tags)) or ["领域知识"]


def _infer_difficulty(content: str) -> str:
    if any(word in content for word in ["边界", "耦合", "扩展", "证据链"]):
        return "进阶"
    if any(word in content for word in ["机理", "表征", "判读"]):
        return "提升"
    return "基础"
