# Gate 5.3: register the UW latency scheduled tasks (idempotent).
#
# The anchors are NEW YORK times (the NYSE session), converted to local wall time
# AT REGISTRATION. Hardcoded Sydney times drift with DST: New York and Sydney
# change on different dates, so a fixed "23:20" is right for only part of the
# year - by mid-October the post-check would fire 45 minutes before the close,
# and by mid-December Windows could kill the collector 45 minutes early.
# Windows triggers cannot track a foreign timezone, so this script must be
# RE-RUN after each DST transition (NY: 2nd Sunday of March / 1st Sunday of
# November; Sydney: 1st Sunday of October / of April). Re-registering the live
# tasks is an owner-authorized action.
# The collector itself is XNYS-calendar aware and exits when there is no session,
# so weekend/holiday firings are harmless no-ops. All tasks StartWhenAvailable.

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot  # this script lives in <repo>/scripts
$uv = (Get-Command uv).Source

$nyZone = [System.TimeZoneInfo]::FindSystemTimeZoneById("Eastern Standard Time")
function Get-LocalTimeForNy {
    param([string]$NyTime)  # "HH:mm" on the New York wall clock
    # Anchor on tomorrow's date so the conversion uses the DST regime of the
    # runs being scheduled, not of the moment someone happens to register.
    $tomorrow = (Get-Date).Date.AddDays(1)
    $parts = $NyTime.Split(":")
    $nyLocal = $tomorrow.AddHours([int]$parts[0]).AddMinutes([int]$parts[1])
    $nyUnspecified = [datetime]::SpecifyKind($nyLocal, "Unspecified")
    $asLocal = [System.TimeZoneInfo]::ConvertTime($nyUnspecified, $nyZone, [System.TimeZoneInfo]::Local)
    return $asLocal.ToString("HH:mm")
}

function Register-MDSTask {
    param([string]$Name, [string]$Arguments, [string]$Time, [string]$Interval = $null)
    $action = New-ScheduledTaskAction -Execute $uv -Argument $Arguments -WorkingDirectory $repo
    # -Daily always, so the trigger re-arms every night. A bare -Once trigger
    # decorated with a repetition fires for its RepetitionDuration and then goes
    # dead: that is how the watchdog stopped after 2026-08-18 06:40 with an empty
    # NextRunTime, leaving three truncated sessions unwatched. The repetition is
    # copied onto the daily trigger instead of replacing it.
    $trigger = New-ScheduledTaskTrigger -Daily -At $Time
    if ($Interval) {
        $pattern = New-ScheduledTaskTrigger -Once -At $Time `
            -RepetitionInterval (New-TimeSpan -Minutes $Interval) `
            -RepetitionDuration (New-TimeSpan -Hours 7)
        $trigger.Repetition = $pattern.Repetition
    }
    # RestartCount matters more than it looks. Windows Update restarts this
    # machine between 22:00 and 04:00 (ActiveHours 04-22), which is inside the
    # 23:20-06:05 collection window, and the reboot kills the collector with
    # 0xC000013A. Measured: 2026-08-18 died 3 minutes before a reboot, 2026-08-21
    # died 20 seconds before one. With RestartCount 0 nothing ever brought it
    # back. Three retries five minutes apart let it resume after the machine
    # returns instead of losing the rest of the session.
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Hours 8) -MultipleInstances IgnoreNew `
        -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5)
    Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
    Write-Host "registered $Name"
}

# NY anchors: collector 10 minutes before the open; watchdog from 09:40 ET;
# post-check 20 minutes after the close; reconcile at 17:00 ET.
Register-MDSTask -Name "MDS650_UW_LatencyCollector" `
    -Arguments "run python scripts/uw_latency_collector.py" -Time (Get-LocalTimeForNy "09:20")
# Interval must match HEARTBEAT_STALE_SECONDS (300s) in uw_latency_verify.py.
# At 30 minutes the watchdog promised 5-minute detection and delivered up to 35:
# on 2026-08-22 it ran at 04:40 against a heartbeat 3 minutes old, found it
# fresh, and the collector had already been dead for seconds.
Register-MDSTask -Name "MDS650_UW_LatencyWatchdog" `
    -Arguments "run python scripts/uw_latency_verify.py --watchdog" -Time (Get-LocalTimeForNy "09:40") -Interval 5
Register-MDSTask -Name "MDS650_UW_LatencyPostCheck" `
    -Arguments "run python scripts/uw_latency_verify.py" -Time (Get-LocalTimeForNy "16:20")
Register-MDSTask -Name "MDS650_UW_LatencyReconcile" `
    -Arguments "run python scripts/uw_latency_reconcile.py" -Time (Get-LocalTimeForNy "17:00")

Get-ScheduledTask -TaskName "MDS650_UW_*" | Select-Object TaskName, State
