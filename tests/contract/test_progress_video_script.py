"""The progress-video runner must keep evidence, recovery, and capture in one script."""

from __future__ import annotations

import re
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
        "cleanup trap": "trap cleanup EXIT INT TERM",
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
