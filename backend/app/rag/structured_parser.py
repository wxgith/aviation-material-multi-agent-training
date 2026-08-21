from __future__ import annotations

import hashlib
import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CORPUS_ROOT = PROJECT_ROOT / "knowledge_corpus"
REGISTRY_PATH = CORPUS_ROOT / "source_registry.json"
PARSED_DIR = CORPUS_ROOT / "parsed_docs"


def parse_registered_structured_sources() -> dict:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    parsed = []
    for source in registry.get("sources", []):
        local_file = source.get("local_file", "")
        path = CORPUS_ROOT / local_file
        suffix = path.suffix.lower()
        if not path.exists() or suffix not in {".xml", ".json"}:
            continue
        if suffix == ".xml":
            markdown, sections = jats_xml_to_markdown(path, source)
            parser_name = "jats-xml"
        elif source.get("document_type") == "open_dataset_metadata":
            markdown, sections = zenodo_json_to_markdown(path, source)
            parser_name = "zenodo-json"
        else:
            continue
        output_path = PARSED_DIR / f"{source['source_id']}.md"
        output_path.write_text(markdown, encoding="utf-8")
        parsed.append(
            {
                "source_id": source["source_id"],
                "parser": parser_name,
                "sections": sections,
                "output": str(output_path.relative_to(PROJECT_ROOT)),
                "sha256": _sha256(path),
            }
        )
    return {"parsed": parsed}


def jats_xml_to_markdown(path: Path, source: dict) -> tuple[str, int]:
    root = ET.parse(path).getroot()
    article_title = _node_text(root.find("./front/article-meta/title-group/article-title"))
    title = article_title or source["title"]
    lines = _frontmatter(source, path, "jats-xml") + [f"# {title}", ""]

    abstract = root.find("./front/article-meta/abstract")
    if abstract is not None:
        lines.extend(["## Abstract", ""])
        for paragraph in abstract.findall(".//p"):
            text = _node_text(paragraph)
            if text:
                lines.extend([text, ""])

    section_count = 0
    for section in root.findall("./body/sec"):
        section_count += _append_section(lines, section, level=2, prefix="")
    return "\n".join(lines), section_count


def zenodo_json_to_markdown(path: Path, source: dict) -> tuple[str, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    metadata = payload.get("metadata", {})
    description = _strip_html(metadata.get("description", ""))
    lines = _frontmatter(source, path, "zenodo-json") + [
        f"# {metadata.get('title') or source['title']}",
        "",
        "## Dataset description",
        "",
        description,
        "",
        "## Experimental record",
        "",
        "The record contains ultrasonic phased-array full-waveform data and processed C-scan images acquired during experimental assessment of impact damage on aerospace composite coupons and laminates.",
        "",
        "## Files and access",
        "",
    ]
    for file in payload.get("files", []):
        lines.append(
            f"- {file.get('key')}: {file.get('size', 0)} bytes; download: {file.get('links', {}).get('self', '')}"
        )
    license_value = metadata.get("license", {})
    license_id = license_value.get("id", "") if isinstance(license_value, dict) else str(license_value)
    lines.extend(
        [
            "",
            "## Provenance and license",
            "",
            f"- DOI: {metadata.get('doi') or source.get('standard_number', '')}",
            f"- Publisher: {metadata.get('publisher', 'Zenodo')}",
            f"- License: {license_id}",
            f"- Resource type: {metadata.get('resource_type', {}).get('title', 'Dataset')}",
            "",
        ]
    )
    return "\n".join(lines), 4


def _append_section(lines: list[str], section: ET.Element, level: int, prefix: str) -> int:
    title = _node_text(section.find("title")) or "Untitled section"
    section_id = section.get("id", "")
    locator = f"{prefix} / {title}".strip(" /")
    heading = f"{title} [{section_id}]" if section_id else title
    lines.extend([f"{'#' * min(level, 4)} {heading}", ""])
    count = 1
    for child in section:
        tag = child.tag.split("}")[-1]
        if tag == "p":
            text = _node_text(child)
            if text:
                lines.extend([text, ""])
        elif tag == "list":
            for item in child.findall("./list-item"):
                text = _node_text(item)
                if text:
                    lines.append(f"- {text}")
            lines.append("")
        elif tag in {"fig", "table-wrap"}:
            caption = _node_text(child.find("caption"))
            label = _node_text(child.find("label"))
            if caption:
                lines.extend([f"{label}: {caption}".strip(": "), ""])
        elif tag == "sec":
            count += _append_section(lines, child, level + 1, locator)
    return count


def _frontmatter(source: dict, path: Path, parser: str) -> list[str]:
    return [
        "---",
        f"source_id: {source['source_id']}",
        f"domain: {source['domain']}",
        f"title: {json.dumps(source['title'], ensure_ascii=False)}",
        f"url: {source.get('url', '')}",
        f"license: {json.dumps(source.get('license_or_authorization', ''), ensure_ascii=False)}",
        f"parser: {parser}",
        f"source_sha256: {_sha256(path)}",
        "review_status: machine_parsed_pending_expert_review",
        "---",
        "",
    ]


def _node_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return re.sub(r"\s+", " ", "".join(node.itertext())).strip()


def _strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> None:
    print(json.dumps(parse_registered_structured_sources(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
