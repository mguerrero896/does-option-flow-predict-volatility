"""Validate the existence, target and future liveness of every MDS650 scheduled task.

MDS650_UW_LatencyWatchdog sat at State=Ready with an empty NextRunTime from
2026-08-18 06:40 onward, because it had been registered from a -Once trigger
carrying a seven-hour repetition rather than a daily one. Nothing noticed, and
the collector ran unwatched through the three sessions that truncated.

The verifier also rejects a missing executable, missing working directory, wrong entrypoint,
expired trigger, unhealthy last exit and the absence of the Phase 9 restart policy. A green
result therefore describes the configured task fleet, not merely the presence of task names.

Usage:
    uv run python scripts/verify_scheduled_tasks.py
    uv run python scripts/verify_scheduled_tasks.py --from-json state.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

# Tasks that must exist. A deleted task reports nothing at all, so absence has
# to be checked separately from health.
EXPECTED = (
    "MDS650_AlertForwarder",
    "MDS650_Knowledge_AutoSync",
    "MDS650_UW_LatencyCollector",
    "MDS650_UW_LatencyWatchdog",
    "MDS650_UW_LatencyPostCheck",
    "MDS650_UW_LatencyReconcile",
    "MDS650_Phase8A_BlindCollector",
    "MDS650_Phase8A_CollectionWatch",
    "MDS650_Phase8A_HealthWatch",
    "MDS650_Phase9_Collector",
    "MDS650_Phase9_PostCheck",
)
# Task names are stable, but a worktree root may be relocated deliberately. Checking the
# entrypoint basename plus the resolved on-disk target catches cross-worktree wiring errors
# without baking one operator's absolute path into the public source.
EXPECTED_ENTRYPOINTS = {
    "MDS650_AlertForwarder": "alert_forwarder.py",
    "MDS650_Knowledge_AutoSync": "sync_project_knowledge.ps1",
    "MDS650_UW_LatencyCollector": "uw_latency_collector.py",
    "MDS650_UW_LatencyWatchdog": "uw_latency_verify.py",
    "MDS650_UW_LatencyPostCheck": "uw_latency_verify.py",
    "MDS650_UW_LatencyReconcile": "uw_latency_reconcile.py",
    "MDS650_Phase8A_BlindCollector": "phase8_run_daily.ps1",
    "MDS650_Phase8A_CollectionWatch": "phase8_watch.ps1",
    "MDS650_Phase8A_HealthWatch": "phase8_health_watch.ps1",
    "MDS650_Phase9_Collector": "phase9_collect.py",
    "MDS650_Phase9_PostCheck": "phase9_verify.py",
}
# A -Once trigger is not wrong by itself: MDS650_AlertForwarder uses one with a
# P3650D repetition and will not expire until 2036. What killed the UW watchdog
# was a -Once trigger whose repetition ran out the same night (PT7H) and never
# re-armed. So the rule is the duration, not the trigger class.
ONE_SHOT_TRIGGER = "MSFT_TaskTimeTrigger"
SHORT_REPETITION = re.compile(r"^PT(?:\d+H|\d+M|\d+S|\d+H\d+M)$")
ACTION_TARGET = re.compile(r'(?:"([^"]+\.(?:py|ps1))"|([^\s"]+\.(?:py|ps1)))', re.I)

POWERSHELL_QUERY = (
    "Get-ScheduledTask | Where-Object { $_.TaskName -match 'MDS650' } | ForEach-Object { "
    "$i = $_ | Get-ScheduledTaskInfo; [PSCustomObject]@{ Name=$_.TaskName; "
    "State=[string]$_.State; Next=[string]$i.NextRunTime; "
    "Trigger=[string]$_.Triggers[0].CimClass.CimClassName; "
    "RepDuration=[string]$_.Triggers[0].Repetition.Duration; "
    "Execute=[string]$_.Actions[0].Execute; Arguments=[string]$_.Actions[0].Arguments; "
    "WorkingDirectory=[string]$_.Actions[0].WorkingDirectory; "
    "RestartCount=[int]$_.Settings.RestartCount; "
    "RestartInterval=[string]$_.Settings.RestartInterval; "
    "LastResult=('0x{0:X8}' -f $i.LastTaskResult) } } | ConvertTo-Json -Depth 3"
)


def action_target(task: dict[str, Any]) -> Path | None:
    """Resolve the first Python/PowerShell entrypoint in a task action."""
    match = ACTION_TARGET.search(str(task.get("Arguments", "")))
    if match is None:
        return None
    target = Path(match.group(1) or match.group(2))
    if target.is_absolute():
        return target
    working_directory = str(task.get("WorkingDirectory", "")).strip()
    return Path(working_directory) / target if working_directory else target


def collect() -> list[dict[str, Any]]:
    """Read live task state via PowerShell."""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", POWERSHELL_QUERY],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise SystemExit(f"cannot read scheduled tasks: {result.stderr.strip()[:200]}")
    parsed = json.loads(result.stdout)
    return parsed if isinstance(parsed, list) else [parsed]


def reasons(
    tasks: list[dict[str, Any]],
    expected: tuple[str, ...] | list[str] = EXPECTED,
) -> list[str]:
    """Return every reason the task fleet cannot be trusted to run."""
    found: list[str] = []
    present = {task.get("Name", "") for task in tasks}
    for name in expected:
        if name not in present:
            found.append(f"{name} does not exist; it was deleted or never registered")

    for task in tasks:
        name = task.get("Name", "<unnamed>")
        if str(task.get("State", "")).lower() == "disabled":
            found.append(f"{name} is disabled")
            continue

        execute = Path(str(task.get("Execute", "")).strip().strip('"'))
        if not execute.is_file():
            found.append(f"{name} executable does not exist: {execute}")
        working_directory = str(task.get("WorkingDirectory", "")).strip()
        if working_directory and not Path(working_directory).is_dir():
            found.append(f"{name} working directory does not exist: {working_directory}")
        target = action_target(task)
        expected_target = EXPECTED_ENTRYPOINTS.get(str(name))
        if target is None:
            found.append(f"{name} action has no Python or PowerShell entrypoint")
        else:
            if expected_target and target.name.lower() != expected_target.lower():
                found.append(
                    f"{name} expected {expected_target} but action targets {target.name}"
                )
            if not target.is_file():
                found.append(f"{name} action target does not exist: {target}")

        if str(name) in ("MDS650_Phase9_Collector", "MDS650_Phase9_PostCheck") and (
            int(task.get("RestartCount", 0)) < 3
            or str(task.get("RestartInterval", "")) != "PT5M"
        ):
            found.append(f"{name} restart policy is not 3 attempts at PT5M")
        if not str(task.get("Next", "")).strip():
            found.append(
                f"{name} is enabled with no next run: its trigger has expired and it "
                "will never fire again"
            )
        duration = str(task.get("RepDuration", "")).strip()
        if task.get("Trigger") == ONE_SHOT_TRIGGER and SHORT_REPETITION.match(duration):
            found.append(
                f"{name} is a one-shot trigger whose repetition ends after {duration} and "
                "never re-arms; a nightly task needs MSFT_TaskDailyTrigger"
            )
        last = str(task.get("LastResult", "0x00000000"))
        if last not in ("0x00000000", "0x00041301", "0x00041303"):
            found.append(f"{name} last exited {last}")
    return found


def check(
    tasks: list[dict[str, Any]],
    expected: tuple[str, ...] | list[str] = EXPECTED,
) -> int:
    return 1 if reasons(tasks, expected) else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-json", type=Path, default=None)
    arguments = parser.parse_args()
    tasks = (
        json.loads(arguments.from_json.read_text(encoding="utf-8"))
        if arguments.from_json
        else collect()
    )
    found = reasons(tasks)
    for reason in found:
        print(f"[tasks] FAIL: {reason}")
    if not found:
        print(
            f"[tasks] {len(tasks)} MDS650 task(s) healthy; enabled, scheduled, "
            "and targeting existing entrypoints"
        )
    raise SystemExit(1 if found else 0)


if __name__ == "__main__":
    main()
