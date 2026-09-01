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
    monkeypatch.setenv("PROGRAMFILES", "C:/Program Files")

    module = _load()
    env = module._ci_sim_env()

    for name in fakes:
        assert name not in env, f"{name} survived the hermetic simulation"
    for value in fakes.values():
        assert value not in env.values(), "a planted secret VALUE survived under another name"
    # The simulation still has to be able to run a subprocess on Windows.
    normalized = {key.upper(): value for key, value in env.items()}
    assert "PATH" in normalized
    assert normalized["PROGRAMFILES"] == "C:/Program Files"
    assert env["MDS650_EXTERNAL_ROOT"].endswith(".ci-sim-nonexistent")
    assert env["MDS650_PANEL_GUARD_MAY_SKIP"] == "1"


def test_licensed_tier2_env_removes_operator_optouts(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("MDS650_PANEL_GUARD_MAY_SKIP", "1")
    monkeypatch.setenv("mds650_uw_latency_freshness_may_skip", "1")
    monkeypatch.setenv("TIER2_HARMLESS_SENTINEL", "preserved")

    env = _load()._licensed_tier2_env()

    names = {name.upper() for name in env}
    assert "MDS650_PANEL_GUARD_MAY_SKIP" not in names
    assert "MDS650_UW_LATENCY_FRESHNESS_MAY_SKIP" not in names
    assert env["TIER2_HARMLESS_SENTINEL"] == "preserved"


def test_full_pytest_receives_the_explicit_licensed_env(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    module = _load()
    monkeypatch.setenv("MDS650_PANEL_GUARD_MAY_SKIP", "1")
    monkeypatch.setenv("MDS650_UW_LATENCY_FRESHNESS_MAY_SKIP", "1")
    calls: dict[str, dict[str, str] | None] = {}

    def record(name, _command, env=None):  # type: ignore[no-untyped-def]
        calls[name] = env
        return 0

    monkeypatch.setattr(module, "_run", record)
    monkeypatch.setattr(module, "_verify_gated_hashes", lambda *_args, **_kwargs: 0)
    with pytest.raises(SystemExit) as exited:
        module.main([])

    assert exited.value.code == 0
    full_env = calls["full-pytest"]
    assert full_env is not None
    full_names = {name.upper() for name in full_env}
    assert "MDS650_PANEL_GUARD_MAY_SKIP" not in full_names
    assert "MDS650_UW_LATENCY_FRESHNESS_MAY_SKIP" not in full_names
    assert calls["ci-sim (hermetic job replica)"]["MDS650_PANEL_GUARD_MAY_SKIP"] == "1"  # type: ignore[index]
    assert calls["ci-sim (hermetic job replica)"]["MDS650_UW_LATENCY_FRESHNESS_MAY_SKIP"] == "1"  # type: ignore[index]


def test_help_exits_without_running_any_gate(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    module = _load()

    def must_not_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        pytest.fail(f"--help executed a gate: {args!r} {kwargs!r}")

    monkeypatch.setattr(module, "_run", must_not_run)
    monkeypatch.setattr(module, "_verify_gated_hashes", must_not_run)
    with pytest.raises(SystemExit) as exited:
        module.main(["--help"])
    assert exited.value.code == 0


def test_existing_evidence_fails_before_running_any_gate(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    module = _load()
    evidence = tmp_path / "already-exists.json"
    evidence.write_text("frozen\n", encoding="utf-8")

    def must_not_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        pytest.fail(f"existing evidence path executed a gate: {args!r} {kwargs!r}")

    monkeypatch.setattr(module, "_run", must_not_run)
    monkeypatch.setattr(module, "_verify_gated_hashes", must_not_run)
    with pytest.raises(SystemExit, match="TIER2_EVIDENCE_ALREADY_EXISTS"):
        module.main(
            [
                "--evidence-output",
                str(evidence),
                "--required-ancestor",
                "HEAD",
            ]
        )


def test_evidence_writer_cannot_overwrite_a_frozen_receipt(tmp_path: Path) -> None:
    module = _load()
    evidence = tmp_path / "already-exists.json"
    evidence.write_text("frozen\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="TIER2_EVIDENCE_ALREADY_EXISTS"):
        module._write_evidence(
            evidence,
            required_ancestor="a" * 40,
            tested_commit="b" * 40,
            tested_tree="c" * 40,
            results={"full-pytest": 0},
        )

    assert evidence.read_text(encoding="utf-8") == "frozen\n"


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

    assert module._verify_gated_hashes() == 0
