from __future__ import annotations

import os
import subprocess
from pathlib import Path

from scripts.scan_public_secrets import (
    _has_github_squash_shape,
    _is_published_main_commit,
    _is_verified_github_squash,
    scan_repository,
)

REPO = Path(__file__).resolve().parents[2]


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


def test_github_squash_identity_requires_a_valid_platform_signature(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.email", "test@users.noreply.github.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "--quiet", "-m", "base")
    tree = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD^{tree}"], text=True
    ).strip()
    parent = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    content = (
        f"tree {tree}\nparent {parent}\n".encode()
        + b"author Test <private@example.invalid> 1 +0000\n"
        b"committer GitHub <noreply@github.com> 1 +0000\n"
        b"gpgsig -----BEGIN PGP SIGNATURE-----\n"
        b" signature\n"
        b" -----END PGP SIGNATURE-----\n\n"
        b"research: result (#16)\n"
    )
    object_id = subprocess.run(
        ["git", "-C", str(repo), "hash-object", "-t", "commit", "-w", "--stdin"],
        input=content,
        capture_output=True,
        check=True,
    ).stdout.decode().strip()
    _git(repo, "update-ref", "refs/remotes/origin/main", parent)
    assert _has_github_squash_shape(content)
    assert not _is_published_main_commit(repo, object_id)
    assert not _is_verified_github_squash(repo, object_id, content)
    assert not _has_github_squash_shape(content.replace(b"gpgsig ", b"unsigned "))
    assert not _has_github_squash_shape(content.replace(b" (#16)", b""))
    assert not _has_github_squash_shape(
        content.replace(b"committer GitHub", b"committer Test")
    )
    assert not _has_github_squash_shape(
        content.replace(b"parent ", b"parent " + b"3" * 40 + b"\nparent ", 1)
    )


def test_published_github_squashes_verify_with_the_pinned_web_flow_key() -> None:
    for object_id in (
        "c39cfb3394aedb020e8a1a3903da66fd603cfd4d",
        "8e19546eae817095f59fc4e15ebfb4c6df2d9e42",
    ):
        content = subprocess.check_output(
            ["git", "-C", str(REPO), "cat-file", "commit", object_id]
        )
        assert _is_published_main_commit(REPO, object_id)
        assert _is_verified_github_squash(REPO, object_id, content)


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
