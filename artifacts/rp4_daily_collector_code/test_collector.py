"""Hermetic, target-blind fixtures; no provider credentials or real collection."""

import io
import json
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from artifacts.rp4_daily_collector_code import collector as c


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("REAL_NETWORK_FORBIDDEN_IN_SYNTHETIC_TEST")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked)
    monkeypatch.setattr(c, "_disk_space", lambda _: None)


def marker(tmp_path):
    root = tmp_path / "new_private_collection"
    root.mkdir()
    config = {"data_root": str(root), "config_sha256": "a" * 64}
    c._write_json(
        root,
        "collector_root.json",
        {
            "task_name": c.TASK_NAME,
            "config_sha256": config["config_sha256"],
        },
    )
    return root, config


def test_plan_holiday_early_close_dst_and_grace(monkeypatch):
    def forbidden(*args):
        raise AssertionError("CREDENTIAL_ACCESS_FORBIDDEN")

    monkeypatch.setattr(c.os.environ, "get", forbidden)
    assert c.plan(datetime(2026, 9, 7, 22, tzinfo=UTC))["session_date"] == "2026-09-04"
    assert c.plan(datetime(2025, 11, 28, 18, 29, tzinfo=UTC))["session_date"] == "2025-11-26"
    assert c.plan(datetime(2025, 11, 28, 18, 30, tzinfo=UTC))["session_date"] == "2025-11-28"
    assert c.plan(datetime(2025, 3, 10, 20, 30, tzinfo=UTC))["session_date"] == "2025-03-10"
    assert c.plan(datetime(2025, 3, 7, 21, 29, tzinfo=UTC))["session_date"] == "2025-03-06"
    with pytest.raises(ValueError, match="TIMEZONE"):
        c.plan(datetime(2026, 9, 7))


def test_config_hash_and_source_drift_block_before_network(tmp_path):
    repo = Path(c.__file__).resolve().parents[2]
    config = {
        "schema": "daily_collection_v1",
        "task_name": c.TASK_NAME,
        "repo_root": str(repo),
        "data_root": str(tmp_path / "data"),
        "source_sha256": {"artifacts/rp4_daily_collector_code/collector.py": "0" * 64},
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="CONFIG_HASH"):
        c.load_config(path, "wrong")
    with pytest.raises(ValueError, match="SOURCE_PIN"):
        c.load_config(path, c.legacy.sha256(path))


def test_kernel_lock_nonblocking_and_released(tmp_path):
    with (
        c.session_lock(tmp_path, date(2026, 9, 4)),
        pytest.raises(OSError),
        c.session_lock(tmp_path, date(2026, 9, 4)),
    ):
        pass
    with c.session_lock(tmp_path, date(2026, 9, 4)):
        pass


def test_collection_same_session_reuses_bytes_and_rejects_corruption(tmp_path, monkeypatch):
    root, config = marker(tmp_path)
    calls = []

    def fixture(path, day, name="tape"):
        calls.append((day, name))
        output = path / "raw" / f"{name}.fixture"
        c.write_bytes_once(output, b"synthetic-not-market-data")
        return [output], {"fixture": True}

    monkeypatch.setattr(c, "download_tape", fixture)
    monkeypatch.setattr(c, "download_bars", fixture)
    now = datetime(2026, 9, 7, 22, tzinfo=UTC)
    assert c.collect(config, now)["status"] == "PASS"
    assert len(calls) == 9 and {day for day, _ in calls} == {date(2026, 9, 4)}
    assert c.collect(config, now)["status"] == "REUSED"
    assert len(calls) == 9
    (root / "raw/tape.fixture").write_bytes(b"changed")
    with pytest.raises(ValueError, match="COMPLETED_BYTES_CHANGED"):
        c.collect(config, now)


def test_five_retries_sanitized_and_other_components_continue(tmp_path, monkeypatch):
    root, config = marker(tmp_path)
    sleeps = []
    monkeypatch.setattr(c.legacy.time, "sleep", sleeps.append)
    failures = []

    def fail(*args):
        failures.append(1)
        raise RuntimeError("fixture-secret-must-not-be-logged")

    def bars(path, day, asset):
        output = path / "raw" / f"{asset}.fixture"
        c.write_bytes_once(output, b"synthetic")
        return [output], {}

    monkeypatch.setattr(c, "download_tape", fail)
    monkeypatch.setattr(c, "download_bars", bars)
    result = c.collect(config, datetime(2026, 9, 7, 22, tzinfo=UTC))
    assert result["status"] == "PARTIAL" and result["missing_components"] == ["uw_tape"]
    assert len(failures) == 5 and sleeps == [1, 2, 4, 8]
    assert len(list((root / "manifests/components/2026-09-04").glob("*.json"))) == 8
    assert not (root / "manifests/sessions/2026-09-04.json").exists()
    assert "fixture-secret" not in next((root / "operations/2026-09-04").glob("*.json")).read_text()


def test_uw_stream_crc_schema_and_future_reuse_without_secret_read(tmp_path, monkeypatch):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as out:
        out.writestr("synthetic.csv", ",".join(c.legacy.tape_core.EVENT_FIELDS) + "\n")
    original = httpx.Client
    requests = []

    def response(request):
        requests.append(request)
        assert request.url.path.endswith("2026-09-04")
        return httpx.Response(200, content=archive.getvalue())

    monkeypatch.setattr(
        c.httpx, "Client", lambda **kw: original(transport=httpx.MockTransport(response), **kw)
    )
    monkeypatch.setattr(c.os.environ, "get", lambda name, *args: "synthetic-key")
    paths, quality = c.download_tape(tmp_path, date(2026, 9, 4))
    assert len(requests) == 1 and quality["crc_valid"] and paths[0].is_file()
    monkeypatch.setattr(c.os.environ, "get", lambda *args: pytest.fail("secret read on reuse"))
    assert c.download_tape(tmp_path, date(2026, 9, 4))[0] == paths
    assert len(requests) == 1


def test_fmp_bounded_dates_partial_coverage_not_imputed(tmp_path, monkeypatch):
    payload = [
        {"date": "2025-11-28 09:30:00", "open": 2, "high": 3, "low": 1, "close": 2, "volume": 5},
        {"date": "2025-11-28 13:00:00", "open": 2, "high": 3, "low": 1, "close": 2, "volume": 5},
    ]

    class Provider:
        def __init__(self, key, max_retries):
            assert max_retries == 1

        def minute_bars(self, asset, from_date, to_date):
            assert (asset, from_date, to_date) == ("AAPL", "2025-11-28", "2025-11-28")
            return SimpleNamespace(payload=payload)

        def close(self):
            pass

    monkeypatch.setattr(c, "FMPProvider", Provider)
    monkeypatch.setattr(c.os.environ, "get", lambda *args: "synthetic-key")
    paths, quality = c.download_bars(tmp_path, date(2025, 11, 28), "AAPL")
    assert quality["rows"] == 1 and quality["expected_minutes"] == 210
    assert quality["missing_minutes"] == 209 and not quality["complete_minute_coverage"]
    assert len(paths) == 2


def test_reuse_rejects_escaped_manifest_path(tmp_path):
    c._write_json(
        tmp_path,
        "manifest.json",
        {
            "status": "PASS",
            "config_sha256": "a",
            "files": [{"relative_path": "../outside", "bytes": 1, "sha256": "a"}],
        },
    )
    with pytest.raises(ValueError, match="OUTSIDE"):
        c._reuse(tmp_path, "manifest.json", "a")


def test_windows_registration_is_disabled_at_source_no_run_action():
    source = Path(__file__).with_name("register_disabled.ps1").read_text()
    assert source.count("<Enabled>false</Enabled>") == 2
    assert "<AllowStartOnDemand>false</AllowStartOnDemand>" in source
    assert "<LogonType>InteractiveToken</LogonType>" in source
    assert "Register-ScheduledTask -TaskName $taskName -TaskPath '\\' -Xml $xml" in source
    assert "Start-ScheduledTask" not in source and "Enable-ScheduledTask" not in source
    assert "-Force" not in source and "-Password" not in source
    assert "DaysInterval>1<" in source
    # The scheduler receives a Unicode BSTR; an explicit UTF-8 declaration fails
    # native validation with SCHED_E_MALFORMEDXML (unable to switch encoding).
    assert '<?xml version="1.0" encoding="UTF-8"?>' not in source


def test_collection_cannot_override_clock_without_dry_run():
    with pytest.raises(SystemExit) as error:
        c.main(
            [
                "--config",
                "unused",
                "--config-sha256",
                "unused",
                "--now",
                "2020-01-01T00:00:00+00:00",
            ]
        )
    assert error.value.code == 2
