"""Operational ``--help`` must never resolve stores, credentials or run work."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = (
    "alert_forwarder",
    "generate_canonical_state",
    "phase9_collect",
    "phase9_verify",
    "sync_supabase_catalog",
    "uw_latency_reconcile",
)


@pytest.mark.parametrize("name", SCRIPTS)
def test_help_exits_before_operational_work(name: str) -> None:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module: Any = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(SystemExit) as exited:
        module.main(["--help"])
    assert exited.value.code == 0
