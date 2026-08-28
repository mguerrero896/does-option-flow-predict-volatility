"""Fail when reachable Git history contains high-confidence secret material.

The scanner reports only the rule, object prefix and path. It never prints the
matched bytes. Run from any directory inside the repository.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

MAX_BLOB_BYTES = 25 * 1024 * 1024
COMMIT_EMAILS = re.compile(rb"^(?:author|committer) .* <([^>\r\n]+)>", re.MULTILINE)
PUBLIC_GIT_EMAIL = re.compile(rb"^[^@\s<>]+@users\.noreply\.github\.com$")

PATTERNS: tuple[tuple[str, re.Pattern[bytes]], ...] = (
    ("aws_access_key", re.compile(rb"(?:A3T[A-Z0-9]|AKIA|ASIA)[A-Z0-9]{16}")),
    ("github_token", re.compile(rb"gh[pousr]_[A-Za-z0-9]{36,255}")),
    ("github_fine_grained_token", re.compile(rb"github_pat_[A-Za-z0-9_]{82,255}")),
    ("google_api_key", re.compile(rb"AIza[0-9A-Za-z_-]{35}")),
    ("slack_token", re.compile(rb"xox[baprs]-[0-9A-Za-z-]{10,}")),
    ("stripe_live_key", re.compile(rb"(?:sk|rk)_live_[0-9A-Za-z]{16,}")),
    (
        "supabase_service_role_jwt",
        re.compile(
            rb"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]*"
            rb"c2VydmljZV9yb2xl[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]+"
        ),
    ),
    ("private_key", re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
)


@dataclass(frozen=True)
class Finding:
    rule: str
    object_id: str
    path: str


def _git(repo: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        input=input_bytes,
        capture_output=True,
        check=True,
    ).stdout


def scan_repository(repo: Path) -> list[Finding]:
    repo_root = Path(_git(repo, "rev-parse", "--show-toplevel").decode().strip())
    objects = _git(repo_root, "rev-list", "--objects", "--all").splitlines()
    paths: dict[str, str] = {}
    object_ids: list[str] = []
    for line in objects:
        object_id, _, path = line.decode("utf-8", errors="replace").partition(" ")
        object_ids.append(object_id)
        if path:
            paths.setdefault(object_id, path)

    batch_input = ("\n".join(object_ids) + "\n").encode()
    batch = _git(repo_root, "cat-file", "--batch", input_bytes=batch_input)
    offset = 0
    findings: list[Finding] = []
    for requested_id in object_ids:
        header_end = batch.index(b"\n", offset)
        header = batch[offset:header_end].decode("ascii", errors="replace")
        offset = header_end + 1
        parts = header.split()
        if len(parts) != 3:
            raise RuntimeError(f"unexpected git cat-file header for {requested_id[:12]}")
        object_id, object_type, size_text = parts
        size = int(size_text)
        content = batch[offset : offset + size]
        offset += size + 1
        if object_type not in {"blob", "commit"}:
            continue
        path = "<commit>" if object_type == "commit" else paths.get(requested_id, "<unknown>")
        if object_type == "blob" and size > MAX_BLOB_BYTES:
            raise RuntimeError(
                f"refusing to skip oversized blob {object_id[:12]} path={path} "
                f"size={size} limit={MAX_BLOB_BYTES}"
            )
        if object_type == "commit" and any(
            not PUBLIC_GIT_EMAIL.fullmatch(email) for email in COMMIT_EMAILS.findall(content)
        ):
            findings.append(Finding("non_noreply_git_identity", object_id, path))
        for rule, pattern in PATTERNS:
            if pattern.search(content):
                findings.append(Finding(rule, object_id, path))
    return findings


def main() -> int:
    findings = scan_repository(Path.cwd())
    if findings:
        for finding in findings:
            print(
                f"SECRET_HISTORY_MATCH rule={finding.rule} "
                f"object={finding.object_id[:12]} path={finding.path}"
            )
        print(f"SECRET_HISTORY_SCAN_FAILED findings={len(findings)}")
        return 1
    print("SECRET_HISTORY_SCAN_OK findings=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
