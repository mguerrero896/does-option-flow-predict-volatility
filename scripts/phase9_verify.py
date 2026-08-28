"""Phase 9 same-day capture verification (decision 59).

Checks that the just-closed session's manifest exists and is complete (bars for
all six assets, tape archive present, quote sweep with OK rows), alerts loudly
on any shortfall, and reports campaign progress toward 60 sessions.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import subprocess
from pathlib import Path

from mds650.config import effective_data_root, production_data_root
from mds650.phase9_contract import (
    TARGET_SESSIONS,
    WINDOW_START,
    capture_problems,
    last_checkpoint,
    last_closed_session,
)

#: The one store whose alerts are real. A desktop popup is global state that no path
#: rebinding can contain, so it is gated on this rather than fired unconditionally:
#: any run against a redirected store - a test, a dry run, a sandbox - is silent on
#: the operator's screen by construction.
PRODUCTION_ROOT: Path | None = None
DATA_ROOT: Path | None = None
STORE: Path | None = None
ALERT: Path | None = None


def _configure_paths() -> None:
    """Resolve operational roots only after CLI parsing (so ``--help`` is inert)."""

    global PRODUCTION_ROOT, DATA_ROOT, STORE, ALERT
    PRODUCTION_ROOT = production_data_root()
    DATA_ROOT = effective_data_root()
    STORE = DATA_ROOT / "phase9"
    ALERT = DATA_ROOT / "logs" / "PHASE9_ALERT.txt"


def _alert(message: str) -> None:
    assert ALERT is not None
    assert DATA_ROOT is not None and PRODUCTION_ROOT is not None
    ALERT.parent.mkdir(parents=True, exist_ok=True)
    with ALERT.open("a", encoding="utf-8") as handle:
        handle.write(f"{dt.datetime.now(dt.UTC).isoformat()} {message}\n")
    with contextlib.suppress(OSError):
        # Only the production store reaches the desktop; a redirected store still
        # records the alert in its own file. Same gate as uw_latency_verify.
        if DATA_ROOT == PRODUCTION_ROOT:
            subprocess.run(
                ["msg", "*", f"MDS650 Phase 9: {message}"],
                check=False,
                capture_output=True,
                timeout=10,
            )
    print(f"[phase9-verify] ALERT: {message}")


def main(argv: list[str] | None = None) -> None:
    argparse.ArgumentParser().parse_args(argv)
    _configure_paths()
    assert STORE is not None
    session = last_closed_session()
    if session is None:
        return
    if session < WINDOW_START:
        print(f"[phase9-verify] session {session} predates the window start; nothing to verify")
        return
    manifest_path = STORE / "raw" / session.isoformat() / "session_manifest.json"
    if not manifest_path.exists():
        checkpoint = last_checkpoint(manifest_path.parent)
        detail = f"; last checkpoint {checkpoint}" if checkpoint else ""
        _alert(f"session {session}: NO manifest (collector missed or still running){detail}")
        raise SystemExit(1)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    problems = capture_problems(manifest)
    counter_path = STORE / "counter.json"
    captured = 0
    if counter_path.exists():
        counter = json.loads(counter_path.read_text(encoding="utf-8"))
        captured = len(counter["sessions"])
        if int(counter.get("reads", 0)) != 0:
            problems.append(f"counter reads={counter.get('reads')}")
    if problems:
        _alert(f"session {session}: capture shortfall ({', '.join(problems)})")
        raise SystemExit(1)
    print(f"[phase9-verify] session {session} complete; campaign {captured}/{TARGET_SESSIONS}")


if __name__ == "__main__":
    main()
