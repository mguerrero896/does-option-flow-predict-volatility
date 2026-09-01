"""The progress-video runner must keep evidence, recovery, and capture in one script."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "record_progress_video.sh"


def test_record_progress_video_script_keeps_the_recording_contract() -> None:
    assert SCRIPT.is_file(), "scripts/record_progress_video.sh is not versioned"
    text = SCRIPT.read_text(encoding="utf-8")

    required = {
        "strict shell": "set -Eeuo pipefail",
        "millisecond chapters": "date +%s%3N",
        "chapter ledger": "VIDEO.chapters",
        "chapter validation": "CHAPTER_LEDGER_INVALID",
        "cleanup trap": "trap cleanup EXIT INT TERM",
        "successful-state cleanup": 'rm -r -- "$STATE_DIR"',
        "clean-worktree gate": "git status --porcelain",
        "native monitor recorder": "gfxcapture=monitor_idx=1",
        "graceful recorder stop": "printf 'q'",
        "video probe": "ffprobe",
        "second terminal": "wt.exe",
        "long evidence gate": "scripts/run_local_evidence_gates.py",
        "licensed-data rejection": "PRE_PUSH_GATED_PATH_REJECTED",
        "freeze mutation test": "test_pit_v22_successor_freeze.py",
        "publication-claim test": "test_sealed_cohort_publication_claims.py",
        "frozen-registry test": "test_frozen_artifacts_registry.py",
        "canonical state": "data/CANONICAL_STATE.json",
        "canonical inference": "rp2_block10_inference/inference.json",
        "figure-open handshake": "EDGE_FIGURE_WINDOW_NOT_FOUND",
        "private guest figure session": '"--guest",',
        "disabled figure sync": '"--disable-sync",',
        "DPI-aware figure placement": "SetProcessDpiAwareness(2)",
        "physical figure placement": "SetWindowPos(",
        "verified figure geometry": "EDGE_FIGURE_GEOMETRY_NOT_VERIFIED",
        "readable figure zoom": 'SendWait("^{ADD}")',
        "interrupt-safe figure cleanup": "ACTIVE_EDGE_PROFILE",
        "figure-close handshake": "EDGE_FIGURE_CLOSE_TIMEOUT",
    }
    missing = [name for name, token in required.items() if token not in text]
    assert not missing, f"progress-video script is missing: {', '.join(missing)}"

    forbidden = {
        "bc dependency": r"\bbc\b",
        "forced ffmpeg termination": r"(?:taskkill|Stop-Process|kill\s+-9)",
        "environment dump": r"(?:^|[;&|]\s*)env(?:\s|$)",
        "dotenv dump": r"cat\s+[^\n]*\.env",
        "superseded estimate": r"\+0\.00096",
        "superseded MDE": r"0\.00129",
        "unspent-successor claim": r"armed.{0,20}unspent",
        "DPI-virtualized recorder": r"\bgdigrab\b",
    }
    found = [name for name, pattern in forbidden.items() if re.search(pattern, text, re.I | re.M)]
    assert not found, f"progress-video script contains forbidden patterns: {', '.join(found)}"

    gate = text[text.index("show_gate_result()") : text.index("show_clean()")]
    assert gate.index("until [[ -s $GATE_DONE ]]") < gate.index("focus-tab --target 1"), (
        "the evidence tab must not be focused until its gate has finished"
    )

    cleanup = text[text.index("cleanup() {") : text.index("trap cleanup")]
    assert 'close_edge_profile "$ACTIVE_EDGE_PROFILE"' in cleanup


def test_chapter_validator_rejects_incomplete_or_impossible_ledgers() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    start = text.index("validate_chapters() {")
    function = text[start : text.index("\n}\n", start) + 3]
    harness = f"""\
set -euo pipefail
die() {{ printf '%s\\n' "$*" >&2; return 1; }}
CH="/tmp/mds650-chapters-$$"
trap 'rm -f "$CH"' EXIT
printf '%s' "$LEDGER" >"$CH"
{function}
validate_chapters "$DURATION_MS"
"""

    valid = """\
0\tACT\t1 | THE QUESTION
100\tACT\t2 | THE MACHINE
200\tACT\t3 | WHAT IT MEASURED
300\tACT\t4 | BREAK IT LIVE
400\tACT\t5 | SCALE AND THE FINAL POSITION
500\tEND\tRecording complete
"""
    invalid = (
        valid.replace("300\tACT", "50\tACT"),
        valid.replace("400\tACT\t5 | SCALE AND THE FINAL POSITION\n", ""),
        valid.replace("500\tEND", "1500\tEND"),
    )

    git_bash = Path(os.environ.get("PROGRAMFILES", "")) / "Git" / "bin" / "bash.exe"
    bash = str(git_bash) if git_bash.is_file() else "bash"
    env = os.environ | {"LEDGER": valid, "DURATION_MS": "1000"}
    result = subprocess.run([bash, "-c", harness], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

    for ledger in invalid:
        env = os.environ | {"LEDGER": ledger, "DURATION_MS": "1000"}
        result = subprocess.run(
            [bash, "-c", harness], env=env, capture_output=True, text=True
        )
        assert result.returncode != 0
        assert "CHAPTER_LEDGER_INVALID" in result.stderr
