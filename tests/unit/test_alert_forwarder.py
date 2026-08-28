from __future__ import annotations

import importlib.util
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "alert_forwarder", ROOT / "scripts" / "alert_forwarder.py"
)
assert SPEC is not None and SPEC.loader is not None
alert_forwarder: Any = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(alert_forwarder)


def _client(statuses: Iterable[int], delivered: list[str]) -> httpx.Client:
    remaining = iter(statuses)

    def handler(request: httpx.Request) -> httpx.Response:
        delivered.append(request.content.decode("utf-8"))
        return httpx.Response(next(remaining), request=request)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_burst_limit_defers_messages_without_dropping_them(tmp_path: Path) -> None:
    log = tmp_path / "alerts.txt"
    state = tmp_path / "state.json"
    log.write_text("".join(f"line-{index}\n" for index in range(12)), encoding="utf-8")
    delivered: list[str] = []

    with _client([200] * 12, delivered) as client:
        first = alert_forwarder.forward_pending(
            client,
            topic="test-topic",
            alert_files={"phase9": log},
            state_path=state,
            burst_limit=10,
        )
        second = alert_forwarder.forward_pending(
            client,
            topic="test-topic",
            alert_files={"phase9": log},
            state_path=state,
            burst_limit=10,
        )

    assert (first, second) == (10, 2)
    assert delivered == [f"line-{index}" for index in range(12)]
    assert json.loads(state.read_text(encoding="utf-8"))["phase9"] == len(
        log.read_text(encoding="utf-8")
    )


def test_http_failure_retries_from_first_unconfirmed_line(tmp_path: Path) -> None:
    log = tmp_path / "alerts.txt"
    state = tmp_path / "state.json"
    log.write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")
    first_attempt: list[str] = []

    with _client([200, 200, 503], first_attempt) as client:
        forwarded = alert_forwarder.forward_pending(
            client,
            topic="test-topic",
            alert_files={"phase8": log},
            state_path=state,
        )

    assert forwarded == 2
    assert first_attempt == ["one", "two", "three"]
    assert json.loads(state.read_text(encoding="utf-8"))["phase8"] == len("one\ntwo\n")

    retry: list[str] = []
    with _client([200, 200], retry) as client:
        forwarded = alert_forwarder.forward_pending(
            client,
            topic="test-topic",
            alert_files={"phase8": log},
            state_path=state,
        )

    assert forwarded == 2
    assert retry == ["three", "four"]
