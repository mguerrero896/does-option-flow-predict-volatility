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
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

CI_IGNORES = [
    "--ignore=tests/unit/test_independent_replication_panel.py",
]
TIER2_FORBIDDEN_OPT_OUTS = frozenset(
    {
        "MDS650_PANEL_GUARD_MAY_SKIP",
        "MDS650_UW_LATENCY_FRESHNESS_MAY_SKIP",
    }
)


def _run(name: str, command: list[str], env: dict[str, str] | None = None) -> int:
    print(f"[tier2] {name}: {' '.join(command)}", flush=True)
    completed = subprocess.run(command, cwd=REPO, env=env)
    status = "PASS" if completed.returncode == 0 else f"FAIL (exit {completed.returncode})"
    print(f"[tier2] {name}: {status}", flush=True)
    return completed.returncode


def _licensed_tier2_env() -> dict[str, str]:
    """Inherit the operator environment except the two licensed-gate exemptions."""

    return {
        name: value
        for name, value in os.environ.items()
        if name.upper() not in TIER2_FORBIDDEN_OPT_OUTS
    }


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


def _verify_gated_hashes(env: dict[str, str] | None = None) -> int:
    pointers = json.loads((REPO / "data" / "GATED_DATA_POINTERS.json").read_text())
    active_env = os.environ if env is None else env
    evidence_root = Path(active_env.get("MDS650_EVIDENCE_ROOT", REPO))
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
    return 1 if failures else 0


def _git_output(*arguments: str, env: dict[str, str]) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=REPO,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _write_evidence(
    path: Path,
    *,
    required_ancestor: str,
    tested_commit: str,
    tested_tree: str,
    results: dict[str, int],
) -> None:
    payload = {
        "schema_version": "mds650-tier2-evidence-v1.0",
        "required_ancestor": required_ancestor,
        "tested_commit": tested_commit,
        "tested_tree": tested_tree,
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "runner": "scripts/run_local_evidence_gates.py",
        "environment_contract": {
            "licensed_gate_opt_outs": {
                name: "absent" for name in sorted(TIER2_FORBIDDEN_OPT_OUTS)
            },
            "ci_sim_declared_opt_outs": {
                name: "1" for name in sorted(TIER2_FORBIDDEN_OPT_OUTS)
            },
        },
        "gates": [
            {"name": name, "exit_code": exit_code}
            for name, exit_code in results.items()
        ],
        "overall_exit_code": 0 if all(code == 0 for code in results.values()) else 1,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except FileExistsError as exc:
        raise SystemExit("TIER2_EVIDENCE_ALREADY_EXISTS") from exc


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-output", type=Path)
    parser.add_argument("--required-ancestor")
    args = parser.parse_args(argv)
    if (args.evidence_output is None) != (args.required_ancestor is None):
        parser.error("--evidence-output and --required-ancestor must be supplied together")

    licensed_env = _licensed_tier2_env()
    required_ancestor = ""
    tested_commit = ""
    tested_tree = ""
    if args.evidence_output is not None:
        evidence_output = args.evidence_output.resolve()
        if evidence_output.exists():
            raise SystemExit("TIER2_EVIDENCE_ALREADY_EXISTS")
        if _git_output("status", "--porcelain", env=licensed_env):
            raise SystemExit("TIER2_EVIDENCE_DIRTY_WORKTREE")
        required_ancestor = _git_output(
            "rev-parse", f"{args.required_ancestor}^{{commit}}", env=licensed_env
        )
        tested_commit = _git_output("rev-parse", "HEAD", env=licensed_env)
        tested_tree = _git_output("rev-parse", "HEAD^{tree}", env=licensed_env)
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", required_ancestor, tested_commit],
            cwd=REPO,
            env=licensed_env,
        )
        if ancestor.returncode != 0:
            raise SystemExit("TIER2_REQUIRED_ANCESTOR_MISSING")

    results = {
        "versioned-hook": _run(
            "versioned-hook",
            ["uv", "run", "python", "scripts/scan_public_secrets.py", "--check-hook"],
            env=licensed_env,
        ),
        "ruff": _run(
            "ruff",
            ["uv", "run", "ruff", "check", "src", "scripts", "tests"],
            env=licensed_env,
        ),
        "mypy": _run(
            "mypy", ["uv", "run", "mypy", "src", "scripts"], env=licensed_env
        ),
        "full-pytest": _run(
            "full-pytest",
            ["uv", "run", "pytest", "tests", "-q"],
            env=licensed_env,
        ),
        "ci-sim": _run(
            "ci-sim (hermetic job replica)",
            ["uv", "run", "pytest", "tests", "-q", *CI_IGNORES,
             "--cov=src/mds650", "--cov-report=term", "--cov-fail-under=90"],
            env=_ci_sim_env(),
        ),
        "gated-hashes": _verify_gated_hashes(licensed_env),
        # The access posture is a published claim about who can read the licensed bucket
        # and its catalog. Until 2026-08-24 it lived only as prose in data/DATA_ACCESS.md
        # and was false for six tables and eight views. The current posture keeps only the
        # six aggregate tables and four curated views open. Tier 2 is where the key exists, so
        # tier 2 is where it gets re-measured; the script exits non-zero when it cannot ask.
        "access-posture": _run(
            "access-posture",
            ["uv", "run", "python", "scripts/verify_access_posture.py"],
            env=licensed_env,
        ),
    }
    overall_exit_code = 0 if all(code == 0 for code in results.values()) else 1
    print(
        "[tier2] summary:",
        {name: "PASS" if code == 0 else f"FAIL ({code})" for name, code in results.items()},
    )
    if args.evidence_output is not None:
        _write_evidence(
            evidence_output,
            required_ancestor=required_ancestor,
            tested_commit=tested_commit,
            tested_tree=tested_tree,
            results=results,
        )
    sys.exit(overall_exit_code)


if __name__ == "__main__":
    main()
