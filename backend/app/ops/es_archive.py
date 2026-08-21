from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from elasticsearch import Elasticsearch, helpers


def create_client(url: str, username: str = "", password: str = "") -> Elasticsearch:
    kwargs: dict[str, Any] = {
        "request_timeout": 30,
        "max_retries": 1,
        "retry_on_timeout": True,
    }
    if username:
        kwargs["basic_auth"] = (username, password)
    return Elasticsearch(url, **kwargs)


def export_index(
    client: Elasticsearch, index: str, output: Path
) -> dict[str, Any]:
    if not client.indices.exists(index=index):
        raise RuntimeError(f"Elasticsearch index does not exist: {index}")
    output.parent.mkdir(parents=True, exist_ok=True)
    index_info = client.indices.get(index=index)[index]
    count = 0
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(
                {
                    "type": "meta",
                    "format_version": 1,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "source_index": index,
                    "mappings": index_info.get("mappings", {}),
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        for hit in helpers.scan(
            client,
            index=index,
            query={"query": {"match_all": {}}},
            preserve_order=False,
        ):
            handle.write(
                json.dumps(
                    {"type": "document", "id": hit["_id"], "source": hit["_source"]},
                    ensure_ascii=False,
                )
                + "\n"
            )
            count += 1
    return {"index": index, "documents": count, "output": str(output)}


def _read_archive(path: Path) -> tuple[dict[str, Any], Iterator[dict[str, Any]]]:
    handle = path.open("r", encoding="utf-8")
    try:
        first = handle.readline()
        if not first:
            raise RuntimeError("Elasticsearch archive is empty.")
        meta = json.loads(first)
        if meta.get("type") != "meta" or meta.get("format_version") != 1:
            raise RuntimeError("Unsupported Elasticsearch archive format.")

        def documents() -> Iterator[dict[str, Any]]:
            try:
                for line_number, line in enumerate(handle, start=2):
                    if not line.strip():
                        continue
                    item = json.loads(line)
                    if item.get("type") != "document" or "id" not in item or "source" not in item:
                        raise RuntimeError(f"Invalid document at archive line {line_number}.")
                    yield item
            finally:
                handle.close()

        return meta, documents()
    except Exception:
        handle.close()
        raise


def restore_index(
    client: Elasticsearch,
    archive: Path,
    target_index: str,
    replace: bool = False,
) -> dict[str, Any]:
    meta, documents = _read_archive(archive)
    exists = bool(client.indices.exists(index=target_index))
    if exists and not replace:
        raise RuntimeError(
            f"Target index exists: {target_index}. Use --replace only after confirming the backup."
        )
    if exists:
        client.indices.delete(index=target_index)
    client.indices.create(index=target_index, mappings=meta.get("mappings", {}))

    actions = (
        {"_op_type": "index", "_index": target_index, "_id": item["id"], "_source": item["source"]}
        for item in documents
    )
    success, errors = helpers.bulk(client, actions, raise_on_error=False, stats_only=False)
    if errors:
        client.indices.delete(index=target_index, ignore_unavailable=True)
        raise RuntimeError(f"Elasticsearch restore failed for {len(errors)} document(s).")
    client.indices.refresh(index=target_index)
    count = int(client.count(index=target_index)["count"])
    if count != success:
        raise RuntimeError(f"Elasticsearch restore count mismatch: bulk={success}, index={count}")
    return {
        "source_index": meta.get("source_index", ""),
        "target_index": target_index,
        "documents": count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export or restore an Elasticsearch index as NDJSON.")
    parser.add_argument("command", choices=["export", "restore"])
    parser.add_argument("--url", required=True)
    parser.add_argument("--index", required=True)
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--username", default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    client = create_client(args.url, args.username, args.password)
    if not client.ping():
        raise SystemExit(f"Elasticsearch is unavailable: {args.url}")
    if args.command == "export":
        result = export_index(client, args.index, args.file)
    else:
        if not args.file.exists():
            raise SystemExit(f"Archive does not exist: {args.file}")
        result = restore_index(client, args.file, args.index, replace=args.replace)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
