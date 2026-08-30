"""An MDS650 scheduled task that will never run again must not look healthy.

MDS650_UW_LatencyWatchdog was registered from a -Once trigger decorated with a
seven-hour repetition. It fired every 30 minutes from 2026-08-17 23:40 until
2026-08-18 06:40 and then went dead. Windows reported it State=Ready with an
empty NextRunTime, which is indistinguishable from healthy at a glance — and
the three sessions that truncated on 08-18, 08-19 and 08-20 all ran unwatched.

An empty NextRunTime on an enabled task is the whole signal. It needs no
heuristics: the task is enabled, so it is meant to run, and Windows is saying it
never will again.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "verify_scheduled_tasks.py"
ALERT_FORWARDER = ROOT / "scripts" / "alert_forwarder.py"
ALERT_FORWARDER_REGISTRATION = ROOT / "scripts" / "register_alert_forwarder_task.ps1"


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("verify_scheduled_tasks", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["verify_scheduled_tasks"] = module
    spec.loader.exec_module(module)
    return module


def _task(name: str, **overrides: Any) -> dict[str, Any]:
    entrypoint = {
        "MDS650_AlertForwarder": "alert_forwarder.py",
        "MDS650_UW_LatencyCollector": "uw_latency_collector.py",
        "MDS650_UW_LatencyWatchdog": "uw_latency_verify.py",
        "MDS650_UW_LatencyPostCheck": "uw_latency_verify.py",
        "MDS650_Phase9_Collector": "phase9_collect.py",
        "MDS650_Phase9_PostCheck": "phase9_verify.py",
    }.get(name, SCRIPT.name)
    task = {
        "Name": name,
        "State": "Ready",
        "Next": "22/08/2026 6:20:00 AM",
        "Trigger": "MSFT_TaskDailyTrigger",
        "LastResult": "0x00000000",
        "RepDuration": "",
        "Execute": sys.executable,
        "Arguments": f"run python scripts/{entrypoint}",
        "WorkingDirectory": str(ROOT),
        "RestartCount": 3,
        "RestartInterval": "PT5M",
    }
    task.update(overrides)
    return task


HEALTHY = [
    _task("MDS650_UW_LatencyCollector"),
    _task("MDS650_UW_LatencyWatchdog"),
    _task("MDS650_UW_LatencyPostCheck"),
]


def test_healthy_fleet_passes() -> None:
    assert _load().reasons(HEALTHY, expected=[]) == []


def test_expired_trigger_is_reported() -> None:
    """The exact 2026-08-18 shape: enabled, Ready, and never running again."""
    module = _load()
    fleet = [*HEALTHY[:2], _task("MDS650_UW_LatencyWatchdog", Next="")]
    found = module.reasons(fleet, expected=[])
    assert found
    assert any("MDS650_UW_LatencyWatchdog" in reason for reason in found)


def test_short_repetition_one_shot_is_reported() -> None:
    """PT7H is what killed the UW watchdog: one window, then silence."""
    module = _load()
    fleet = [
        _task("MDS650_UW_LatencyWatchdog", Trigger="MSFT_TaskTimeTrigger", RepDuration="PT7H")
    ]
    assert module.reasons(fleet, expected=[])


def test_long_repetition_one_shot_is_not_reported() -> None:
    """MDS650_AlertForwarder uses P3650D and does not expire until 2036."""
    module = _load()
    fleet = [
        _task("MDS650_AlertForwarder", Trigger="MSFT_TaskTimeTrigger", RepDuration="P3650D")
    ]
    assert module.reasons(fleet, expected=[]) == []


def test_disabled_expected_task_is_reported() -> None:
    module = _load()
    fleet = [_task("MDS650_Knowledge_AutoSync", State="Disabled", Next="")]
    assert any("disabled" in reason for reason in module.reasons(fleet, expected=[]))


def test_retired_phase8_task_must_remain_disabled() -> None:
    module = _load()
    fleet = [
        _task(
            "MDS650_Phase8A_BlindCollector",
            State="Disabled",
            Next="",
            Arguments="-File scripts/phase8_run_daily.ps1",
        )
    ]
    assert module.reasons(fleet, expected=[]) == []


def test_reactivated_phase8_task_is_reported() -> None:
    module = _load()
    fleet = [
        _task(
            "MDS650_Phase8A_BlindCollector",
            State="Ready",
            Arguments="-File scripts/phase8_run_daily.ps1",
        )
    ]
    found = module.reasons(fleet, expected=[])
    assert any("must remain disabled" in reason for reason in found)


def test_failing_last_result_is_reported() -> None:
    module = _load()
    fleet = [_task("MDS650_UW_LatencyCollector", LastResult="0xE0434352")]
    found = module.reasons(fleet, expected=[])
    assert "MDS650_UW_LatencyCollector last exited 0xE0434352" in found


def test_missing_expected_task_is_reported() -> None:
    """A task that was deleted cannot be observed as unhealthy; it must be named."""
    module = _load()
    found = module.reasons([_task("MDS650_UW_LatencyCollector")], expected=["MDS650_Absent_Task"])
    assert any("MDS650_Absent_Task" in reason for reason in found)


def test_phase9_tasks_are_required() -> None:
    module = _load()
    assert {"MDS650_Phase9_Collector", "MDS650_Phase9_PostCheck"} <= set(module.EXPECTED)


def test_phase8_health_and_isolated_knowledge_tasks_are_required() -> None:
    module = _load()
    assert {"MDS650_Phase8A_HealthWatch", "MDS650_Knowledge_AutoSync"} <= set(
        module.EXPECTED
    )


def test_wrong_or_missing_action_target_is_reported() -> None:
    module = _load()
    wrong = _task(
        "MDS650_Phase9_Collector",
        Arguments="run python scripts/not_the_collector.py",
    )
    found = module.reasons([wrong], expected=[])
    assert any("expected phase9_collect.py" in reason for reason in found)
    assert any("does not exist" in reason for reason in found)


def test_missing_working_directory_is_reported(tmp_path: Path) -> None:
    module = _load()
    missing = _task("MDS650_Phase9_Collector", WorkingDirectory=str(tmp_path / "gone"))
    assert any("working directory does not exist" in reason for reason in module.reasons(
        [missing], expected=[]
    ))


def test_phase9_requires_restart_after_transient_failure() -> None:
    module = _load()
    no_retry = _task("MDS650_Phase9_Collector", RestartCount=0, RestartInterval="")
    assert any("restart policy" in reason for reason in module.reasons([no_retry], expected=[]))


def test_phase9_registration_has_three_five_minute_retries() -> None:
    source = (ROOT / "scripts" / "register_phase9_tasks.ps1").read_text(encoding="utf-8")
    assert "-RestartCount 3" in source
    assert "-RestartInterval (New-TimeSpan -Minutes 5)" in source
    assert "[string]$RepositoryRoot" in source


def test_alert_forwarder_is_required_and_registered_every_thirty_minutes() -> None:
    module = _load()
    source = ALERT_FORWARDER_REGISTRATION.read_text(encoding="utf-8")
    assert "MDS650_AlertForwarder" in module.EXPECTED
    assert "-Minutes 30" in source
    assert "-Days 3650" in source


def test_alert_forwarder_requires_delivery_without_logging_topic() -> None:
    source = ALERT_FORWARDER.read_text(encoding="utf-8")
    assert "response.raise_for_status()" in source
    assert "topic={topic}" not in source


def test_check_returns_exit_code() -> None:
    module = _load()
    assert module.check(HEALTHY, expected=[]) == 0
    assert module.check([_task("MDS650_UW_LatencyWatchdog", Next="")], expected=[]) == 1
