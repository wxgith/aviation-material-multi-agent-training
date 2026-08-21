import json

import pytest

from app.ops.es_archive import _read_archive


def test_read_archive_streams_documents(tmp_path):
    archive = tmp_path / "knowledge.ndjson"
    archive.write_text(
        "\n".join(
            [
                json.dumps({"type": "meta", "format_version": 1, "source_index": "source"}),
                json.dumps({"type": "document", "id": "one", "source": {"title": "A"}}),
                json.dumps({"type": "document", "id": "two", "source": {"title": "B"}}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    meta, documents = _read_archive(archive)

    assert meta["source_index"] == "source"
    assert [item["id"] for item in documents] == ["one", "two"]


def test_read_archive_rejects_unknown_format(tmp_path):
    archive = tmp_path / "bad.ndjson"
    archive.write_text(json.dumps({"type": "meta", "format_version": 9}) + "\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Unsupported"):
        _read_archive(archive)
