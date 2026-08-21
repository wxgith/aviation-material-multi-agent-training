"""Create a UTF-8-safe ZIP for the reviewer release directory."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path


def create_zip(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise SystemExit(f"Source directory does not exist: {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        destination,
        mode="w",
        compression=zipfile.ZIP_STORED,
        allowZip64=True,
    ) as archive:
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            archive.write(path, (Path(source.name) / path.relative_to(source)).as_posix())


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: create_release_zip.py <source-directory> <destination.zip>")
    create_zip(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
