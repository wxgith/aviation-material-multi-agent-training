from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CORPUS_ROOT = PROJECT_ROOT / "knowledge_corpus"
REGISTRY_PATH = CORPUS_ROOT / "source_registry.json"
MANIFEST_PATH = CORPUS_ROOT / "index_manifest.json"


def build_source_catalog(domain: str | None = None, query: str | None = None) -> dict:
    registry = _read_json(REGISTRY_PATH, {"sources": []})
    manifest = _read_json(MANIFEST_PATH, {"sources": [], "chunks": []})
    chunk_counts = {
        item["source_id"]: item.get("chunks", 0)
        for item in manifest.get("sources", [])
    }
    indexed_sources = {
        item.get("source_id")
        for item in manifest.get("chunks", [])
        if item.get("indexed_in_es")
    }
    manifest_authorities = {}
    for item in manifest.get("chunks", []):
        source_id = item.get("source_id")
        authority = item.get("source_authority")
        if source_id and authority:
            manifest_authorities.setdefault(source_id, authority)

    normalized_domain = (domain or "").strip().lower()
    normalized_query = (query or "").strip().lower()
    sources = []
    for source in registry.get("sources", []):
        if normalized_domain and source.get("domain") != normalized_domain:
            continue
        searchable = " ".join(
            [
                source.get("source_id", ""),
                source.get("title", ""),
                source.get("author_or_org", ""),
                source.get("standard_number", ""),
                " ".join(source.get("applicable_sections", [])),
            ]
        ).lower()
        if normalized_query and normalized_query not in searchable:
            continue
        source_id = source["source_id"]
        sources.append(
            {
                "source_id": source_id,
                "domain": source.get("domain", "general"),
                "title": source.get("title", source_id),
                "author_or_org": source.get("author_or_org", ""),
                "year": source.get("year"),
                "document_type": source.get("document_type", ""),
                "standard_number": source.get("standard_number", ""),
                "url": source.get("url", ""),
                "license_or_authorization": source.get("license_or_authorization", ""),
                "source_authority": source.get("source_authority")
                or manifest_authorities.get(source_id, "metadata_only"),
                "applicable_sections": source.get("applicable_sections", []),
                "acquisition_status": source.get("acquisition_status", "pending"),
                "chunk_count": chunk_counts.get(source_id, 0),
                "indexed_in_es": source_id in indexed_sources,
                "notes": source.get("notes", ""),
            }
        )

    sources.sort(
        key=lambda item: (
            item["domain"],
            0 if item["indexed_in_es"] else 1,
            -(item["year"] or 0),
            item["title"],
        )
    )
    domain_counts = Counter(item["domain"] for item in sources)
    authority_counts = Counter(item["source_authority"] for item in sources)
    return {
        "summary": {
            "registry_updated_at": registry.get("updated_at", ""),
            "source_count": len(sources),
            "indexed_source_count": sum(item["indexed_in_es"] for item in sources),
            "total_chunks": sum(item["chunk_count"] for item in sources),
            "manifest_total_chunks": manifest.get("total_chunks", 0),
            "es_index": manifest.get("index_name", ""),
            "indexed_in_es": manifest.get("indexed_in_es", False),
            "domain_counts": dict(sorted(domain_counts.items())),
            "authority_counts": dict(sorted(authority_counts.items())),
        },
        "sources": sources,
    }


def _read_json(path: Path, fallback: dict) -> dict:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback
