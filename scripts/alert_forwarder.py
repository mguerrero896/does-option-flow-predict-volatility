"""Forward unattended campaign alerts to ntfy with at-least-once delivery.

The per-file character checkpoint advances after each confirmed HTTP response. A process
crash between the response and the atomic checkpoint can duplicate that one message; it
cannot silently skip the rest of a burst. Runs every 30 minutes through the
MDS650_AlertForwarder scheduled task.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import secrets
from collections.abc import Mapping
from pathlib import Path

import httpx

from mds650.config import effective_data_root


def _alert_files(logs: Path) -> dict[str, Path]:
    return {
        "phase8": logs / "PHASE8_ALERT.txt",
        "uw_latency": logs / "UW_LATENCY_ALERT.txt",
        "phase9": logs / "PHASE9_ALERT.txt",
    }


def _topic(logs: Path) -> str:
    logs.mkdir(parents=True, exist_ok=True)
    topic_file = logs / "ntfy_topic.txt"
    if topic_file.exists():
        return topic_file.read_text(encoding="utf-8").strip()
    topic = f"mds650-{secrets.token_hex(8)}"
    topic_file.write_text(topic + "\n", encoding="utf-8")
    return topic


def _read_state(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or any(
        not isinstance(name, str) or not isinstance(offset, int) or offset < 0
        for name, offset in raw.items()
    ):
        raise RuntimeError("ALERT_FORWARDER_STATE_INVALID")
    return raw


def _write_state(path: Path, state: Mapping[str, int]) -> None:
    """Persist a confirmed checkpoint without exposing a partially written JSON file."""

    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(dict(state), indent=1) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def forward_pending(
    client: httpx.Client,
    *,
    topic: str,
    alert_files: Mapping[str, Path],
    state_path: Path,
    burst_limit: int = 10,
) -> int:
    """Forward pending lines and checkpoint each confirmed delivery.

    The burst limit is a per-file rate limit, not a truncation rule. Unsent lines remain
    behind the persisted offset and are processed during the next scheduled run.
    """

    if burst_limit < 1:
        raise ValueError("ALERT_FORWARDER_BURST_LIMIT_INVALID")
    state = _read_state(state_path)
    forwarded = 0
    for name, path in alert_files.items():
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        offset = int(state.get(name, 0))
        if offset > len(content):
            # A rotated/truncated log is a new stream. Resetting is safer than waiting for
            # it to grow past an offset that belongs to the previous file.
            offset = 0
            state[name] = 0
            _write_state(state_path, state)
        if offset == len(content):
            continue

        cursor = offset
        sent_for_file = 0
        for chunk in content[offset:].splitlines(keepends=True):
            if sent_for_file >= burst_limit:
                break
            next_cursor = cursor + len(chunk)
            line = chunk.rstrip("\r\n")
            if line.strip():
                try:
                    response = client.post(
                        f"https://ntfy.sh/{topic}",
                        content=line.encode("utf-8"),
                        headers={
                            "Title": f"MDS650 {name} alert",
                            "Priority": "high",
                            "Tags": "rotating_light",
                        },
                    )
                    response.raise_for_status()
                except httpx.HTTPError:
                    return forwarded
                forwarded += 1
                sent_for_file += 1
            state[name] = next_cursor
            _write_state(state_path, state)
            cursor = next_cursor
    return forwarded


def main(argv: list[str] | None = None) -> None:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    data_root = effective_data_root()
    logs = data_root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=30) as client:
        forwarded = forward_pending(
            client,
            topic=_topic(logs),
            alert_files=_alert_files(logs),
            state_path=logs / "alert_forwarder_state.json",
        )
    stamp = dt.datetime.now(dt.UTC).isoformat()
    print(f"[alert-forwarder] {stamp} forwarded={forwarded}")


if __name__ == "__main__":
    main()
