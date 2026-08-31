"""A clone must expose when the versioned pre-push hook is not active."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VERIFY = REPO / "scripts" / "scan_public_secrets.py"
VERSIONED_HOOK = REPO / "scripts" / "hooks" / "pre-push"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True, env=env
    )


def _fresh_clone_fixture(tmp_path: Path) -> Path:
    repo = tmp_path / "clone"
    (repo / "scripts" / "hooks").mkdir(parents=True)
    shutil.copyfile(VERSIONED_HOOK, repo / "scripts" / "hooks" / "pre-push")
    (repo / "README.md").write_text("fixture\n", encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "contract@example.invalid")
    _git(repo, "config", "user.name", "Contract Test")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "fixture")
    return repo


def _verify(repo: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    return subprocess.run(
        [sys.executable, str(VERIFY), "--check-hook"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )


def test_fresh_clone_without_hooks_path_fails_loudly(tmp_path: Path) -> None:
    result = _verify(_fresh_clone_fixture(tmp_path))
    assert result.returncode == 1
    assert result.stderr.strip() == "PRE_PUSH_HOOKS_PATH_UNSET"


def test_hooks_path_pointing_elsewhere_is_a_distinct_failure(tmp_path: Path) -> None:
    repo = _fresh_clone_fixture(tmp_path)
    (repo / ".githooks").mkdir()
    shutil.copyfile(VERSIONED_HOOK, repo / ".githooks" / "pre-push")
    _git(repo, "config", "core.hooksPath", ".githooks")

    result = _verify(repo)

    assert result.returncode == 1
    assert result.stderr.strip() == "PRE_PUSH_HOOKS_PATH_WRONG"


def test_correct_path_with_nonversioned_bytes_is_a_distinct_failure(tmp_path: Path) -> None:
    repo = _fresh_clone_fixture(tmp_path)
    _git(repo, "config", "core.hooksPath", "scripts/hooks")
    hook = repo / "scripts" / "hooks" / "pre-push"
    hook.write_text(hook.read_text(encoding="utf-8") + "# drift\n", encoding="utf-8")

    result = _verify(repo)

    assert result.returncode == 1
    assert result.stderr.strip() == "PRE_PUSH_HOOK_BYTES_MISMATCH"


def test_correct_versioned_hook_is_accepted(tmp_path: Path) -> None:
    repo = _fresh_clone_fixture(tmp_path)
    _git(repo, "config", "core.hooksPath", "scripts/hooks")

    result = _verify(repo)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "PRE_PUSH_HOOK_OK"


def test_this_clone_uses_the_versioned_hook() -> None:
    result = _verify(REPO)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "PRE_PUSH_HOOK_OK"
