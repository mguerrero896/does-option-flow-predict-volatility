"""The hermetic-simulation environment, pinned with FAKE secrets.

The previous implementation stripped a blocklist and misspelled the one secret
that matters: it removed ``UNUSUAL_WHALES_API_KEY`` while the application reads
``UNUSUALWHALES_API_KEY`` — so the "no keys" simulation ran with the real key in
its environment. An allowlist cannot fail that way: a misspelled entry breaks the
simulation loudly instead of leaking silently. This test proves it with planted
fakes (no real secret is read or printed).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load():  # type: ignore[no-untyped-def]  # a script module has no stub
    spec = importlib.util.spec_from_file_location(
        "run_local_evidence_gates", ROOT / "scripts" / "run_local_evidence_gates.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_no_planted_secret_survives_the_simulation_env(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fakes = {
        "UNUSUALWHALES_API_KEY": "fake-uw",
        "UNUSUAL_WHALES_API_KEY": "fake-uw-misspelled",
        "FMP_API_KEY": "fake-fmp",
        "MDS650_FMP_API_KEY": "fake-fmp-2",
        "MASSIVE_API_KEY": "fake-massive",
        "SUPABASE_SERVICE_KEY": "fake-supabase",
        "SUPABASE_ANON_KEY": "fake-anon",
        "MDS650_EVIDENCE_ROOT": "D:/fake",
        "MDS650_DATA_ROOT": "D:/fake2",
        "SOME_FUTURE_PROVIDER_KEY": "fake-future",
    }
    for name, value in fakes.items():
        monkeypatch.setenv(name, value)

    module = _load()
    env = module._ci_sim_env()

    for name in fakes:
        assert name not in env, f"{name} survived the hermetic simulation"
    for value in fakes.values():
        assert value not in env.values(), "a planted secret VALUE survived under another name"
    # The simulation still has to be able to run a subprocess on Windows.
    assert "PATH" in {k.upper() for k in env}
    assert env["MDS650_EXTERNAL_ROOT"].endswith(".ci-sim-nonexistent")
    assert env["MDS650_PANEL_GUARD_MAY_SKIP"] == "1"


def test_help_exits_without_running_any_gate(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    module = _load()

    def must_not_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        pytest.fail(f"--help executed a gate: {args!r} {kwargs!r}")

    monkeypatch.setattr(module, "_run", must_not_run)
    monkeypatch.setattr(module, "_verify_gated_hashes", must_not_run)
    with pytest.raises(SystemExit) as exited:
        module.main(["--help"])
    assert exited.value.code == 0


def test_ci_does_not_hide_portable_byte_contracts() -> None:
    module = _load()
    portable = {
        "tests/unit/test_generate_date_level_pit_preflight_plan_v1.py",
        "tests/unit/test_date_level_pit_preflight_request_budget_v1.py",
        "tests/contract/test_b2_confirmation_inputs.py",
    }
    ignored = {argument.removeprefix("--ignore=") for argument in module.CI_IGNORES}

    assert ignored == {"tests/unit/test_independent_replication_panel.py"}
    assert portable.isdisjoint(ignored)

    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    publisher = (ROOT / "scripts" / "publish_mirror.sh").read_text(encoding="utf-8")
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "*.yml text eol=lf" in attributes
    assert "*.yaml text eol=lf" in attributes
    for path in portable:
        assert f"--ignore={path}" not in workflow
        assert f"--ignore={path}" not in publisher


def test_gated_hashes_use_the_explicit_evidence_root(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    module = _load()
    repo = tmp_path / "repo"
    evidence = tmp_path / "evidence"
    (repo / "data").mkdir(parents=True)
    artifact = evidence / "artifacts" / "panel.parquet"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"licensed-derived")
    (repo / "data" / "GATED_DATA_POINTERS.json").write_text(
        json.dumps(
            {
                "files": [
                    {
                        "path": "artifacts/panel.parquet",
                        "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "REPO", repo)
    monkeypatch.setenv("MDS650_EVIDENCE_ROOT", str(evidence))

    assert module._verify_gated_hashes()
