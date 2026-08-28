"""Deterministic source-tree identities for authorization-gated executables."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def _normalized_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def build_executable_closure(
    repository: Path,
    *,
    scripts: Iterable[str],
) -> dict[str, Any]:
    """Hash explicit script dependencies plus the complete importable package tree.

    The broad package inclusion is deliberate: a one-shot read is rarer and costlier than a
    re-freeze, while trying to infer Python's dynamic import graph risks omitting executable
    code. Paths and normalized file hashes are both included so the closure is auditable.
    """

    relative_paths = {Path(path) for path in scripts}
    relative_paths.update(
        path.relative_to(repository) for path in (repository / "src" / "mds650").rglob("*.py")
    )
    files: list[dict[str, str]] = []
    for relative in sorted(relative_paths, key=lambda path: path.as_posix()):
        source = repository / relative
        if not source.is_file():
            raise FileNotFoundError(f"EXECUTABLE_CLOSURE_SOURCE_MISSING:{relative.as_posix()}")
        files.append({"path": relative.as_posix(), "sha256": _normalized_sha256(source)})
    encoded = json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "algorithm": "sha256-of-sorted-path-and-normalized-sha256-v1",
        "file_count": len(files),
        "files": files,
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }
