from __future__ import annotations

import json
from pathlib import Path

from app.core.config import settings
from app.rag.chunker import ChunkingConfig, chunk_markdown_file
from app.rag.embedder import embed_texts, embedding_status
from app.search.es_client import es_connected, get_es_client
from app.services.data_loader import load_knowledge_base


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CORPUS_ROOT = PROJECT_ROOT / "knowledge_corpus"
PARSED_DIR = CORPUS_ROOT / "parsed_docs"
CHUNKS_DIR = CORPUS_ROOT / "chunks"
REGISTRY_PATH = CORPUS_ROOT / "source_registry.json"


def build_chunks_from_parsed_docs() -> list[dict]:
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    registry = _load_registry()
    all_chunks: list[dict] = []
    for path in sorted(PARSED_DIR.glob("*.md")):
        source = registry.get(path.stem, {})
        domain = source.get("domain") or _domain_from_name(path.stem)
        config = ChunkingConfig(
            domain=domain,
            source_id=path.stem,
            title_prefix=source.get("title", path.stem),
            source_url=source.get("url", ""),
            source_authority=source.get(
                "source_authority", "official_primary" if source else "curated_local"
            ),
        )
        chunks = chunk_markdown_file(path, config)
        out_path = CHUNKS_DIR / f"{path.stem}.chunks.json"
        out_path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
        all_chunks.extend(chunks)
    return all_chunks


def _load_registry() -> dict[str, dict]:
    if not REGISTRY_PATH.exists():
        return {}
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {source["source_id"]: source for source in payload.get("sources", [])}


def attach_embeddings(chunks: list[dict]) -> tuple[list[dict], dict]:
    status = embedding_status()
    texts = [f"{chunk.get('title', '')}\n{chunk.get('content', '')}" for chunk in chunks]
    embeddings = embed_texts(texts)
    if embeddings is None:
        return chunks, {**status, "embedded": False}
    for chunk, embedding in zip(chunks, embeddings):
        chunk["embedding"] = embedding
    return chunks, {**status, "embedded": True, "count": len(embeddings)}


def index_chunks(chunks: list[dict]) -> int:
    if not settings.es_enabled or not es_connected():
        return 0
    from app.search.indexer import ensure_index

    ensure_index()
    client = get_es_client()
    client.indices.put_mapping(
        index=settings.es_index_knowledge,
        properties={
            "source_id": {"type": "keyword"},
            "source_locator": {"type": "keyword"},
            "source_url": {"type": "keyword", "index": False},
            "source_authority": {"type": "keyword"},
        },
    )
    count = 0
    for chunk in chunks:
        client.index(index=settings.es_index_knowledge, id=chunk["id"], document=chunk)
        count += 1
    client.indices.refresh(index=settings.es_index_knowledge)
    return count


def run_pipeline() -> dict:
    parsed_chunks = build_chunks_from_parsed_docs()
    base_chunks = _load_base_chunks()
    chunks = base_chunks + parsed_chunks
    chunks, embedding_info = attach_embeddings(chunks)
    indexed = index_chunks(chunks)
    manifest_path = _write_manifest(chunks, indexed > 0)
    return {
        "parsed_docs": len(list(PARSED_DIR.glob("*.md"))),
        "base_json_chunks": len(base_chunks),
        "parsed_document_chunks": len(parsed_chunks),
        "chunks": len(chunks),
        "embedding": embedding_info,
        "indexed_to_es": indexed,
        "es_index": settings.es_index_knowledge,
        "manifest": str(manifest_path.relative_to(PROJECT_ROOT)),
    }


def _load_base_chunks() -> list[dict]:
    chunks = []
    for domain, knowledge in load_knowledge_base().items():
        for original in knowledge.get("chunks", []):
            chunk = dict(original)
            chunk.setdefault("source_id", f"local_json_{domain}")
            chunk.setdefault("source_locator", chunk.get("title", chunk["id"]))
            chunk.setdefault("source_url", "")
            chunk.setdefault("source_authority", "curated_local")
            chunk.setdefault("chunk_file", f"backend/app/data/knowledge_{domain}.json")
            chunks.append(chunk)
    return chunks


def _write_manifest(chunks: list[dict], indexed: bool) -> Path:
    manifest_path = CORPUS_ROOT / "index_manifest.json"
    sources: dict[str, dict] = {}
    for chunk in chunks:
        source = sources.setdefault(
            chunk["source_id"],
            {"source_id": chunk["source_id"], "domain": chunk["domain"], "chunks": 0},
        )
        source["chunks"] += 1
    payload = {
        "index_name": settings.es_index_knowledge,
        "retrieval_modes": ["bm25", "vector", "hybrid"],
        "embedding": embedding_status(),
        "total_chunks": len(chunks),
        "indexed_in_es": indexed,
        "sources": sorted(sources.values(), key=lambda item: item["source_id"]),
        "chunks": [
            {
                "id": chunk["id"],
                "domain": chunk["domain"],
                "title": chunk["title"],
                "tags": chunk.get("tags", []),
                "difficulty": chunk.get("difficulty", ""),
                "source_id": chunk.get("source_id", ""),
                "source_locator": chunk.get("source_locator", ""),
                "source_url": chunk.get("source_url", ""),
                "source_authority": chunk.get("source_authority", "curated_local"),
                "chunk_file": chunk.get(
                    "chunk_file", f"chunks/{chunk['source_id']}.chunks.json"
                ),
                "indexed_in_es": indexed,
            }
            for chunk in chunks
        ],
    }
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


def _domain_from_name(name: str) -> str:
    lowered = name.lower()
    if "tire" in lowered:
        return "tire"
    if "brake" in lowered:
        return "brake"
    if "composite" in lowered:
        return "composite"
    return "general"


def main() -> None:
    print(json.dumps(run_pipeline(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
