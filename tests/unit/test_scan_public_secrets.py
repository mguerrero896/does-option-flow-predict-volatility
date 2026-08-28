from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.scan_public_secrets import scan_repository


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_scanner_finds_secret_deleted_from_tip_without_echoing_it(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.email", "test@users.noreply.github.com")
    _git(repo, "config", "user.name", "Test")

    secret = "AK" + "IA" + "A" * 16
    tracked = repo / "removed.txt"
    tracked.write_text(secret, encoding="utf-8")
    _git(repo, "add", "removed.txt")
    _git(repo, "commit", "--quiet", "-m", "add fixture")
    tracked.unlink()
    _git(repo, "add", "-u")
    _git(repo, "commit", "--quiet", "-m", "remove fixture")

    findings = scan_repository(repo)

    assert [(item.rule, item.path) for item in findings] == [("aws_access_key", "removed.txt")]
    assert all(secret not in repr(item) for item in findings)


def test_scanner_rejects_personal_git_identity_without_echoing_it(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    email = "private@example.invalid"
    _git(repo, "config", "user.email", email)
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("public\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "--quiet", "-m", "add fixture")

    findings = scan_repository(repo)

    assert [(item.rule, item.path) for item in findings] == [
        ("non_noreply_git_identity", "<commit>")
    ]
    assert all(email not in repr(item) for item in findings)
