"""A test must not be able to raise a desktop alert on the operator's screen.

`scripts/uw_latency_verify.py` writes every shortfall to an alert file and also fires a
Windows `msg *` popup. `tests/contract/test_uw_latency_fail_closed.py` rebinds DATA_ROOT to
a throwaway store, which isolates the file - and does nothing about the popup, because a
desktop notification is global and no path rebinding can contain it. Running the contract
suite therefore fired eleven popups at the operator in two minutes, every one of them a
synthetic fixture describing a session that was already known and already over.

The cost is not the interruption. It is that a week before a sealed cohort is read once and
cannot be re-read, the operator is being trained to dismiss MDS650 popups on sight - so the
one alert that will matter arrives already discounted.

The fix ties the popup to the same switch that already isolates the file: the alert store
has to be the production one. Any test that redirects DATA_ROOT is then silent by
construction, including tests nobody has written yet.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "uw_latency_verify.py"


def _load(monkeypatch: pytest.MonkeyPatch, root: Path):
    monkeypatch.setenv("MDS650_DATA_ROOT", str(root / "production"))
    monkeypatch.setenv("MDS650_EXTERNAL_ROOT", str(root))
    sys.modules.pop("uw_latency_verify", None)
    spec = importlib.util.spec_from_file_location("uw_latency_verify", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["uw_latency_verify"] = module
    spec.loader.exec_module(module)
    return module


def test_a_redirected_store_never_reaches_the_desktop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With DATA_ROOT pointed at a scratch directory, no subprocess may be spawned."""
    verifier = _load(monkeypatch, tmp_path)

    spawned: list[list[str]] = []
    monkeypatch.setattr(
        verifier.subprocess, "run", lambda cmd, **kw: spawned.append(list(cmd))
    )

    verifier._alert("synthetic failure from a test")

    assert not spawned, (
        f"a test raised {len(spawned)} desktop notification(s) on the operator's screen: "
        f"{spawned}"
    )
    written = (tmp_path / "logs" / "UW_LATENCY_ALERT.txt").read_text(encoding="utf-8")
    assert "synthetic failure from a test" in written, (
        "the alert must still be recorded in the redirected store; only the popup is muted"
    )


def test_the_production_store_still_raises_one(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Muting must be tied to redirection, not applied to every run.

    Otherwise the repair silences the alert it exists to deliver.
    """
    verifier = _load(monkeypatch, tmp_path)

    spawned: list[list[str]] = []
    monkeypatch.setattr(
        verifier.subprocess, "run", lambda cmd, **kw: spawned.append(list(cmd))
    )
    monkeypatch.setattr(verifier, "DATA_ROOT", verifier.PRODUCTION_ROOT)

    verifier._alert("a real shortfall")

    assert len(spawned) == 1, "the production store must still reach the desktop"
    assert spawned[0][0] == "msg"


def test_no_script_fires_an_ungated_desktop_popup() -> None:
    """The class, not the instance.

    Three scripts fired `msg *`; fixing one and leaving two is the incomplete
    correction this project treats as its own defect. This pins the rule for scripts
    nobody has written yet: if a module spawns a desktop notification, the call must
    sit under a comparison against its production store.
    """
    offenders: list[str] = []
    for script in sorted((ROOT / "scripts").glob("*.py")):
        body = script.read_text(encoding="utf-8", errors="replace")
        if '"msg", "*"' not in body:
            continue
        if "PRODUCTION_ROOT" not in body:
            offenders.append(f"{script.name}: spawns a popup with no production gate")
            continue
        gated = any(
            "== PRODUCTION_ROOT" in line and line.strip().startswith("if ")
            for line in body.splitlines()
        )
        if not gated:
            offenders.append(
                f"{script.name}: declares PRODUCTION_ROOT but never gates on it"
            )

    separator = chr(10) + "  "
    assert not offenders, "ungated desktop notifications:" + separator + separator.join(
        offenders
    )
