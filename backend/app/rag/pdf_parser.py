from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CORPUS_ROOT = PROJECT_ROOT / "knowledge_corpus"
REGISTRY_PATH = CORPUS_ROOT / "source_registry.json"
PARSED_DIR = CORPUS_ROOT / "parsed_docs"


def parse_registered_pdfs() -> dict:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    parsed = []
    skipped = []
    for source in registry.get("sources", []):
        local_file = source.get("local_file", "")
        if not local_file.lower().endswith(".pdf"):
            continue
        pdf_path = CORPUS_ROOT / local_file
        if not pdf_path.exists():
            skipped.append({"source_id": source["source_id"], "reason": "file_not_found"})
            continue
        markdown, page_count = pdf_to_markdown(pdf_path, source)
        output_path = PARSED_DIR / f"{source['source_id']}.md"
        output_path.write_text(markdown, encoding="utf-8")
        parsed.append(
            {
                "source_id": source["source_id"],
                "output": str(output_path.relative_to(PROJECT_ROOT)),
                "pages": page_count,
                "sha256": _sha256(pdf_path),
            }
        )
    return {"parsed": parsed, "skipped": skipped}


def pdf_to_markdown(pdf_path: Path, source: dict) -> tuple[str, int]:
    executable = shutil.which("pdftotext")
    if executable is None:
        raise RuntimeError("pdftotext is required. Install Poppler or add pdftotext to PATH.")
    result = subprocess.run(
        [executable, "-layout", "-enc", "UTF-8", str(pdf_path), "-"],
        check=True,
        capture_output=True,
    )
    text = result.stdout.decode("utf-8", errors="replace")
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()

    header = [
        "---",
        f"source_id: {source['source_id']}",
        f"domain: {source['domain']}",
        f"title: {_yaml_text(source['title'])}",
        f"url: {source.get('url', '')}",
        f"parser: pdftotext-layout",
        f"source_sha256: {_sha256(pdf_path)}",
        "review_status: machine_parsed_pending_expert_review",
        "---",
        "",
        f"# {source['title']}",
        "",
    ]
    body = []
    selected_pages = _parse_page_ranges(source.get("ingest_page_ranges", ""), len(pages))
    for page_number, page in enumerate(pages, start=1):
        if page_number not in selected_pages:
            continue
        cleaned = _clean_page(page)
        if not cleaned:
            continue
        body.extend([f"## Page {page_number}", "", cleaned, ""])
    return "\n".join(header + body), len(selected_pages)


def _parse_page_ranges(value: str, page_count: int) -> set[int]:
    if not value:
        return set(range(1, page_count + 1))
    pages: set[int] = set()
    for token in value.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            start_text, end_text = token.split("-", 1)
            start, end = int(start_text), int(end_text)
            pages.update(range(max(1, start), min(page_count, end) + 1))
        else:
            page = int(token)
            if 1 <= page <= page_count:
                pages.add(page)
    return pages


def _clean_page(page: str) -> str:
    page = page.replace("\x00", "")
    lines = [re.sub(r"[ \t]+$", "", line) for line in page.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def _yaml_text(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> None:
    print(json.dumps(parse_registered_pdfs(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
