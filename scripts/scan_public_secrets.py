"""Fail when public Git history contains high-confidence secret material.

The scanner reports only the rule, object prefix and path. It never prints the
matched bytes. Public history means the current checkout and origin remote refs;
CI also passes ``--include-tags`` because its clean clone contains only public
tags. Unrelated local archive refs are not publication inputs. Run from any
directory inside the repository.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

COMMIT_EMAILS = re.compile(rb"^(?:author|committer) .* <([^>\r\n]+)>", re.MULTILINE)
PUBLIC_GIT_EMAIL = re.compile(
    rb"^(?:[^@\s<>]+@users\.noreply\.github\.com|noreply@github\.com)$"
)
GITHUB_MERGE_COMMITTER = re.compile(
    rb"^committer GitHub <noreply@github\.com> ", re.MULTILINE
)
GITHUB_SYNTHETIC_MERGE_MESSAGE = re.compile(
    rb"^Merge [0-9a-f]{40} into [0-9a-f]{40}\n?$"
)
GITHUB_SQUASH_SUBJECT = re.compile(rb"^[^\r\n]+ \(#[1-9][0-9]*\)$")
GITHUB_WEB_FLOW_KEY = Path(__file__).with_name("github_web_flow_signing_key.asc")
# Source: https://api.github.com/users/web-flow/gpg_keys, key B5690EEEBB952194.
GITHUB_WEB_FLOW_FINGERPRINT = "968479A1AFF927E37D1A566BB5690EEEBB952194"
PUBLIC_REVISIONS = ("--remotes=origin", "HEAD")
VERSIONED_PRE_PUSH = Path("scripts/hooks/pre-push")

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


def check_versioned_pre_push_hook(repo: Path) -> str | None:
    """Return a stable failure code when Git would not execute the tracked hook."""

    repo_root = Path(_git(repo, "rev-parse", "--show-toplevel").decode().strip())
    configured = subprocess.run(
        ["git", "-C", str(repo_root), "config", "--get", "core.hooksPath"],
        capture_output=True,
        check=False,
    )
    if configured.returncode == 1 or not configured.stdout.strip():
        return "PRE_PUSH_HOOKS_PATH_UNSET"
    if configured.returncode != 0:
        raise RuntimeError("cannot resolve core.hooksPath")

    active = Path(
        _git(
            repo_root,
            "rev-parse",
            "--path-format=absolute",
            "--git-path",
            "hooks/pre-push",
        )
        .decode()
        .strip()
    ).resolve()
    expected = (repo_root / VERSIONED_PRE_PUSH).resolve()
    if os.path.normcase(str(active)) != os.path.normcase(str(expected)):
        return "PRE_PUSH_HOOKS_PATH_WRONG"

    versioned = _git(repo_root, "cat-file", "blob", f"HEAD:{VERSIONED_PRE_PUSH.as_posix()}")
    if not active.is_file() or active.read_bytes() != versioned:
        return "PRE_PUSH_HOOK_BYTES_MISMATCH"
    return None


def _is_github_synthetic_merge(content: bytes) -> bool:
    """Recognise GitHub's temporary two-parent PR test merge."""
    headers, separator, message = content.partition(b"\n\n")
    return bool(
        separator
        and sum(line.startswith(b"parent ") for line in headers.splitlines()) == 2
        and GITHUB_MERGE_COMMITTER.search(headers)
        and GITHUB_SYNTHETIC_MERGE_MESSAGE.fullmatch(message)
    )


def _has_github_squash_shape(content: bytes) -> bool:
    """Recognize the one-parent squash envelope emitted by GitHub."""

    headers, separator, message = content.partition(b"\n\n")
    subject = message.splitlines()[0] if message else b""
    return bool(
        separator
        and sum(line.startswith(b"parent ") for line in headers.splitlines()) == 1
        and GITHUB_MERGE_COMMITTER.search(headers)
        and b"\ngpgsig -----BEGIN PGP SIGNATURE-----\n" in headers
        and GITHUB_SQUASH_SUBJECT.fullmatch(subject)
    )


def _gpg_program() -> str | None:
    configured = subprocess.run(
        ["git", "config", "--get", "gpg.program"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    if configured:
        return configured
    if located := shutil.which("gpg"):
        return located
    git = shutil.which("git")
    if os.name == "nt" and git:
        bundled = Path(git).resolve().parents[1] / "usr" / "bin" / "gpg.exe"
        if bundled.is_file():
            return str(bundled)
    return None


def _gpg_path(path: Path) -> str:
    resolved = path.resolve()
    if os.name == "nt":
        drive, tail = resolved.as_posix().split(":", 1)
        return f"/{drive.lower()}{tail}"
    return str(resolved)


def _is_published_main_commit(repo: Path, object_id: str) -> bool:
    history = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "rev-list",
            "--first-parent",
            "refs/remotes/origin/main",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return history.returncode == 0 and object_id in history.stdout.splitlines()


def _is_verified_github_squash(repo: Path, object_id: str, content: bytes) -> bool:
    """Accept a published-main squash only when GitHub's pinned key verifies it."""

    gpg = _gpg_program()
    if (
        not _has_github_squash_shape(content)
        or not _is_published_main_commit(repo, object_id)
        or not gpg
        or not GITHUB_WEB_FLOW_KEY.is_file()
    ):
        return False
    with tempfile.TemporaryDirectory(prefix="mds650-gpg-") as gpg_home:
        env = os.environ.copy()
        env["GNUPGHOME"] = _gpg_path(Path(gpg_home))
        imported = subprocess.run(
            [gpg, "--batch", "--quiet", "--import", _gpg_path(GITHUB_WEB_FLOW_KEY)],
            capture_output=True,
            env=env,
            check=False,
        )
        if imported.returncode != 0:
            return False
        verified = subprocess.run(
            [
                "git",
                "-c",
                f"gpg.program={Path(gpg).as_posix()}",
                "-C",
                str(repo),
                "verify-commit",
                "--raw",
                object_id,
            ],
            capture_output=True,
            env=env,
            check=False,
        )
    valid_signature = (
        f"[GNUPG:] VALIDSIG {GITHUB_WEB_FLOW_FINGERPRINT} ".encode()
    )
    return verified.returncode == 0 and valid_signature in verified.stdout + verified.stderr


def scan_repository(repo: Path, *, include_tags: bool = False) -> list[Finding]:
    repo_root = Path(_git(repo, "rev-parse", "--show-toplevel").decode().strip())
    revisions = (*PUBLIC_REVISIONS, "--tags") if include_tags else PUBLIC_REVISIONS
    objects = _git(repo_root, "rev-list", "--objects", *revisions).splitlines()
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
        if object_type == "commit":
            has_private_identity = any(
                not PUBLIC_GIT_EMAIL.fullmatch(email)
                for email in COMMIT_EMAILS.findall(content)
            )
            if (
                has_private_identity
                and not _is_github_synthetic_merge(content)
                and not _is_verified_github_squash(repo_root, object_id, content)
            ):
                findings.append(Finding("non_noreply_git_identity", object_id, path))
        for rule, pattern in PATTERNS:
            if pattern.search(content):
                findings.append(Finding(rule, object_id, path))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-tags",
        action="store_true",
        help="scan local tags too (use in a clean public clone)",
    )
    parser.add_argument(
        "--check-hook",
        action="store_true",
        help="verify that Git would execute the byte-exact tracked pre-push hook",
    )
    arguments = parser.parse_args()
    if arguments.check_hook:
        failure = check_versioned_pre_push_hook(Path.cwd())
        if failure:
            print(failure, file=sys.stderr)
            return 1
        print("PRE_PUSH_HOOK_OK")
        return 0
    findings = scan_repository(Path.cwd(), include_tags=arguments.include_tags)
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
