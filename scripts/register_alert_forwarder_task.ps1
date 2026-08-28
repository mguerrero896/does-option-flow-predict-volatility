$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$uv = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
if (-not (Test-Path -LiteralPath $uv -PathType Leaf)) {
    throw "uv executable not found: $uv"
}

$action = New-ScheduledTaskAction `
    -Execute $uv `
    -Argument "run python scripts/alert_forwarder.py" `
    -WorkingDirectory $repo
# Task Scheduler has no native "every 30 minutes forever" trigger. The long-lived -Once
# repetition is intentional; the liveness verifier rejects short -Once windows that expire.
$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 30) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

Register-ScheduledTask `
    -TaskName "MDS650_AlertForwarder" `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Forward MDS650 operational alerts every 30 minutes." `
    -Force | Out-Null

Get-ScheduledTask -TaskName "MDS650_AlertForwarder" |
    Select-Object TaskName, State
