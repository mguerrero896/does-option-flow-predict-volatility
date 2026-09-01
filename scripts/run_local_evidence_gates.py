"""Tier-2 validation: the local, licensed-evidence gates (CI cannot run these).

Runs, with true exit codes, everything the hosted hermetic CI deliberately
excludes: the FULL pytest suite (local-store contracts included), SHA-256
verification of every gated file against data/GATED_DATA_POINTERS.json, and the
static gates for parity. Exit code 0 means the tier-2 claim "the complete suite
passes locally against the real evidence" is verified, not asserted.

Run:  uv run python scripts/run_local_evidence_gates.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

CI_IGNORES = [
    "--ignore=tests/unit/test_independent_replication_panel.py",
]


def _run(name: str, command: list[str], env: dict[str, str] | None = None) -> bool:
    print(f"[tier2] {name}: {' '.join(command)}", flush=True)
    completed = subprocess.run(command, cwd=REPO, env=env)
    status = "PASS" if completed.returncode == 0 else f"FAIL (exit {completed.returncode})"
    print(f"[tier2] {name}: {status}", flush=True)
    return completed.returncode == 0


def _ci_sim_env() -> dict[str, str]:
    """Approximate the hosted runner: no evidence root, no external drive, no keys.

    Every hermetic-CI platform gap this simulation can catch is caught BEFORE a
    publish, so a red run (and its failure email) never reaches GitHub.
    """
    # An allowlist, not a blocklist: the blocklist version silently kept the real
    # UW key because it stripped "UNUSUAL_WHALES_API_KEY" while the application
    # reads "UNUSUALWHALES_API_KEY" (no underscore). A misspelled allowlist entry
    # breaks the simulation loudly; a misspelled blocklist entry leaks a secret
    # silently. `tests/unit/test_evidence_gates_env.py` pins that fake secrets do
    # not survive this function.
    keep = (
        "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "OS",
        "TEMP", "TMP", "LOCALAPPDATA", "APPDATA", "PROGRAMDATA", "PROGRAMFILES",
        "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "USERNAME",
        "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE", "PROCESSOR_IDENTIFIER",
        "PROCESSOR_LEVEL", "PROCESSOR_REVISION",
        "PYTHONIOENCODING", "VIRTUAL_ENV", "UV_CACHE_DIR",
    )
    env = {name: value for name, value in os.environ.items() if name.upper() in keep}
    env["MDS650_EXTERNAL_ROOT"] = str(REPO / ".ci-sim-nonexistent")
    env["MDS650_PANEL_GUARD_MAY_SKIP"] = "1"
    env["MDS650_UW_LATENCY_FRESHNESS_MAY_SKIP"] = "1"
    return env


def _verify_gated_hashes() -> bool:
    pointers = json.loads((REPO / "data" / "GATED_DATA_POINTERS.json").read_text())
    evidence_root = Path(os.environ.get("MDS650_EVIDENCE_ROOT", REPO))
    failures = []
    for entry in pointers["files"]:
        path = evidence_root / entry["path"]
        if not path.is_file():
            failures.append(f"MISSING {entry['path']}")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            failures.append(f"HASH_MISMATCH {entry['path']}")
    for failure in failures:
        print(f"[tier2] gated-hashes: {failure}")
    print(f"[tier2] gated-hashes: {'PASS' if not failures else 'FAIL'} "
          f"({len(pointers['files']) - len(failures)}/{len(pointers['files'])} verified)")
    return not failures


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    results = {
        "versioned-hook": _run(
            "versioned-hook",
            ["uv", "run", "python", "scripts/scan_public_secrets.py", "--check-hook"],
        ),
        "ruff": _run("ruff", ["uv", "run", "ruff", "check", "src", "scripts", "tests"]),
        "mypy": _run("mypy", ["uv", "run", "mypy", "src", "scripts"]),
        "full-pytest": _run("full-pytest", ["uv", "run", "pytest", "tests", "-q"]),
        "ci-sim": _run(
            "ci-sim (hermetic job replica)",
            ["uv", "run", "pytest", "tests", "-q", *CI_IGNORES,
             "--cov=src/mds650", "--cov-report=term", "--cov-fail-under=90"],
            env=_ci_sim_env(),
        ),
        "gated-hashes": _verify_gated_hashes(),
        # The access posture is a published claim about who can read the licensed bucket
        # and its catalog. Until 2026-08-24 it lived only as prose in data/DATA_ACCESS.md
        # and was false for six tables and eight views. The current posture keeps only the
        # six aggregate tables and four curated views open. Tier 2 is where the key exists, so
        # tier 2 is where it gets re-measured; the script exits non-zero when it cannot ask.
        "access-posture": _run(
            "access-posture", ["uv", "run", "python", "scripts/verify_access_posture.py"]
        ),
    }
    print("[tier2] summary:", {name: "PASS" if ok else "FAIL" for name, ok in results.items()})
    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
