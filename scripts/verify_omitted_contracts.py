"""Run exactly the contracts omitted by a prior public JUnit report; require zero skips."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REQUIRED_ROOTS = (
    "MDS650_EVIDENCE_ROOT",
    "MDS650_DATA_ROOT",
    "MDS650_EXTERNAL_ROOT",
    "MDS650_RP2_PANEL_ROOT",
    "MDS650_REPO_ROOT",
    "MDS650_RP4_AUDIT_ROOT",
)


def omitted_nodes(path: Path) -> list[str]:
    nodes = []
    for case in ET.parse(path).iter("testcase"):
        if case.find("skipped") is None:
            continue
        module, name = case.get("classname", ""), case.get("name", "")
        if not re.fullmatch(r"tests\.contract\.test_[a-z0-9_]+", module):
            raise ValueError("ONLY_REVIEWED_CONTRACT_MODULES_SUPPORTED")
        if not re.fullmatch(r"test_[a-z0-9_]+(?:\[[A-Za-z0-9_-]+\])?", name):
            raise ValueError("INVALID_CONTRACT_NODE")
        nodes.append(module.replace(".", "/") + ".py::" + name)
    if not nodes or len(nodes) != len(set(nodes)):
        raise ValueError("EMPTY_OR_DUPLICATE_SELECTION")
    return nodes


def complete(report: Path, expected: list[str]) -> bool:
    cases = list(ET.parse(report).iter("testcase"))
    actual = [c.get("classname", "").replace(".", "/") + ".py::" + c.get("name", "") for c in cases]
    return sorted(actual) == sorted(expected) and all(
        c.find(tag) is None for c in cases for tag in ("skipped", "failure", "error")
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection-junit", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    nodes = omitted_nodes(args.selection_junit)
    if len(nodes) != args.expected_count:
        parser.error("SELECTION_COUNT_MISMATCH")
    environment = os.environ.copy()
    for key in ("MDS650_PANEL_GUARD_MAY_SKIP", "MDS650_UW_LATENCY_FRESHNESS_MAY_SKIP"):
        environment.pop(key, None)
    for key in REQUIRED_ROOTS:
        if not environment.get(key) or not Path(environment[key]).is_dir():
            parser.error(f"CONFIGURED_DIRECTORY_REQUIRED: {key}")
    output = args.output_dir.resolve()
    if output.is_relative_to(REPO):
        parser.error("KEEP_LICENSED_TEST_LOGS_OUTSIDE_REPOSITORY")
    output.mkdir(parents=True, exist_ok=False)
    report = output / "contracts.xml"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *nodes, f"--junitxml={report}"],
        cwd=REPO,
        env=environment,
        capture_output=True,
    )
    (output / "pytest.log").write_bytes(result.stdout + result.stderr)
    passed = result.returncode == 0 and report.is_file() and complete(report, nodes)
    receipt = {
        "status": "PASS" if passed else "FAIL",
        "selected": len(nodes),
        "zero_skips_required": True,
        "pytest_exit_code": result.returncode,
        "selection_sha256": hashlib.sha256(args.selection_junit.read_bytes()).hexdigest(),
        "tested_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO)
        .decode()
        .strip(),
        "dirty_tree": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO)),
        "nodes": nodes,
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"{receipt['status']}: {len(nodes)} selected contracts; zero skips required")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
