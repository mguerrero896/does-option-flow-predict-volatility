# Phase 9 scheduled tasks (decision 59 activation). Idempotent.
# NY close 16:00 = 06:00 AEST next day; collector fires 09:45 local. That is the
# earliest locally observed slot that produced complete manifests on four sessions;
# 08:10 raced the provider's daily Full Tape publication and left partial sessions.
# The collector is XNYS-aware (no-op on non-sessions), and the post-check verifies the manifest at
# 13:30 local (the Massive sweep takes ~90-100 minutes at 5 req/min pacing).
# Three five-minute retries cover transient process/provider failures only. They rerun the
# same scheduled action; they do not select an earlier session or authorize backfill.

[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$uv = (Get-Command uv).Source

function Register-P9Task {
    param([string]$Name, [string]$Arguments, [string]$Time)
    $action = New-ScheduledTaskAction -Execute $uv -Argument $Arguments -WorkingDirectory $repo
    $trigger = New-ScheduledTaskTrigger -Daily -At $Time
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 5) -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5)
    Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
    Write-Host "registered $Name"
}

Register-P9Task -Name "MDS650_Phase9_Collector" `
    -Arguments "run python scripts/phase9_collect.py" -Time "09:45"
Register-P9Task -Name "MDS650_Phase9_PostCheck" `
    -Arguments "run python scripts/phase9_verify.py" -Time "13:30"

Get-ScheduledTask -TaskName "MDS650_Phase9_*" | Select-Object TaskName, State
