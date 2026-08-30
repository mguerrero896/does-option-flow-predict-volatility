from __future__ import annotations

import os
import subprocess
from pathlib import Path

from scripts.scan_public_secrets import APPROVED_NON_NOREPLY_COMMITS, scan_repository


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

    commit = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    assert scan_repository(
        repo, allowed_non_noreply_commits=frozenset({commit})
    ) == []


def test_only_the_published_pr14_squash_identity_is_excepted() -> None:
    expected = frozenset({"c39cfb3394aedb020e8a1a3903da66fd603cfd4d"})
    assert expected == APPROVED_NON_NOREPLY_COMMITS


def test_scanner_accepts_github_service_identity(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.email", "noreply@github.com")
    _git(repo, "config", "user.name", "GitHub")
    (repo / "README.md").write_text("public\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "--quiet", "-m", "service fixture")

    assert scan_repository(repo) == []


def test_scanner_accepts_only_a_github_synthetic_pr_merge(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "--quiet", "--initial-branch=main")
    _git(repo, "config", "user.email", "test@users.noreply.github.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "--quiet", "-m", "base")
    base = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    _git(repo, "switch", "--quiet", "-c", "feature")
    (repo / "feature.txt").write_text("feature\n", encoding="utf-8")
    _git(repo, "add", "feature.txt")
    _git(repo, "commit", "--quiet", "-m", "feature")
    head = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    _git(repo, "switch", "--quiet", "main")
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Test User",
            "GIT_AUTHOR_EMAIL": "private@example.invalid",
            "GIT_COMMITTER_NAME": "GitHub",
            "GIT_COMMITTER_EMAIL": "noreply@github.com",
        }
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "merge",
            "--quiet",
            "--no-ff",
            "feature",
            "-m",
            f"Merge {head} into {base}",
        ],
        check=True,
        capture_output=True,
        env=env,
    )

    assert scan_repository(repo) == []
