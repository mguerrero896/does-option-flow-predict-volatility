[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$RepoRoot,
    [Parameter(Mandatory)][string]$DataRoot,
    [Parameter(Mandatory)][string]$UvPath,
    [Parameter(Mandatory)][string]$PythonEnvironment,
    [ValidatePattern('^[a-z0-9_]+$')][string]$SetupRevision = 'registration_v1',
    [switch]$PrepareOnly
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$taskName = 'OptionsVolatility-Daily-Collection'

function Write-NewUtf8([string]$Path, [string]$Text) {
    $bytes = [Text.UTF8Encoding]::new($false).GetBytes($Text + "`n")
    $stream = [IO.File]::Open($Path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write)
    try { $stream.Write($bytes, 0, $bytes.Length) } finally { $stream.Dispose() }
}
function PrivateAcl([string]$Path, [string]$OwnerSid) {
    $acl = [System.Security.AccessControl.DirectorySecurity]::new()
    $acl.SetAccessRuleProtection($true, $false)
    $acl.SetOwner([System.Security.Principal.SecurityIdentifier]::new($OwnerSid))
    foreach ($sid in @($OwnerSid, 'S-1-5-18', 'S-1-5-32-544')) {
        $acl.AddAccessRule([System.Security.AccessControl.FileSystemAccessRule]::new(
            [System.Security.Principal.SecurityIdentifier]::new($sid),
            'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow'))
    }
    Set-Acl -LiteralPath $Path -AclObject $acl
}
function TaskCensus {
    $rows = @()
    foreach ($task in Get-ScheduledTask) {
        if ($task.TaskName -eq $taskName -and $task.TaskPath -eq '\') { continue }
        $xml = Export-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath
        $digest = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($xml))).ToLowerInvariant()
        $rows += @{ task_name = $task.TaskName; task_path = $task.TaskPath; definition_sha256 = $digest }
    }
    return @($rows | Sort-Object task_path, task_name)
}

try {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
    $UvPath = (Resolve-Path -LiteralPath $UvPath).Path
    $PythonEnvironment = (Resolve-Path -LiteralPath $PythonEnvironment).Path
    $DataRoot = [IO.Path]::GetFullPath($DataRoot)
    if (Test-Path -LiteralPath $DataRoot) { throw 'NEW_DATA_ROOT_ALREADY_EXISTS' }
    if (Get-ScheduledTask -TaskName $taskName -TaskPath '\' -ErrorAction SilentlyContinue) { throw 'TASK_ALREADY_EXISTS' }
    $privateRoot = Join-Path $RepoRoot ('artifacts/rp4_daily_collector_setup/private/' + $SetupRevision)
    if (Test-Path -LiteralPath $privateRoot) { throw 'SETUP_PRIVATE_ROOT_ALREADY_EXISTS' }
    $ownerSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $null = [IO.Directory]::CreateDirectory($privateRoot)
    PrivateAcl $privateRoot $ownerSid
    $sources = @(
        'artifacts/rp4_daily_collector_code/collector.py',
        'artifacts/rp4_daily_collector_code/launch.ps1',
        'artifacts/rp4_code/acquire.py', 'artifacts/rp4_code/evaluate.py',
        'scripts/download_calibration_20d.py',
        'src/mds650/providers/fmp.py', 'src/mds650/providers/base.py',
        'src/mds650/normalize.py', 'src/mds650/contracts.py', 'src/mds650/time.py',
        'src/mds650/errors.py', 'src/mds650/phase5_storage.py', 'src/mds650/study_design.py',
        'src/mds650/b1q_exogenous_provenance_v1.py', 'uv.lock', 'pyproject.toml'
    )
    $pins = @{}
    foreach ($relative in $sources) {
        $pins[$relative] = (Get-FileHash -LiteralPath (Join-Path $RepoRoot $relative) -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    $config = @{
        schema = 'daily_collection_v1'; task_name = $taskName; repo_root = $RepoRoot
        data_root = $DataRoot; uv_path = $UvPath; python_environment = $PythonEnvironment
        owner_sid = $ownerSid; source_sha256 = $pins
    }
    $configPath = Join-Path $privateRoot 'machine_config.json'
    Write-NewUtf8 $configPath ($config | ConvertTo-Json -Depth 8)
    $configSha = (Get-FileHash -LiteralPath $configPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $before = TaskCensus
    Write-NewUtf8 (Join-Path $privateRoot 'other_tasks_before.json') ($before | ConvertTo-Json -Depth 8)
    $shellPath = (Get-Command pwsh -ErrorAction Stop).Source
    $launcherPath = Join-Path $RepoRoot 'artifacts/rp4_daily_collector_code/launch.ps1'
    $actionArgs = '-NoLogo -NoProfile -NonInteractive -WindowStyle Hidden -File "' + $launcherPath + '" -ConfigPath "' + $configPath + '" -ConfigSha256 ' + $configSha
    $nextBoundary = (Get-Date).ToUniversalTime().Date.AddDays(1).AddHours(22).ToString('yyyy-MM-ddTHH:mm:ssZ')
    $eShell = [Security.SecurityElement]::Escape($shellPath)
    $eArgs = [Security.SecurityElement]::Escape($actionArgs)
    $eRepo = [Security.SecurityElement]::Escape($RepoRoot)
    $xml = @"
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>Private target-blind latest-closed-session collection. Created disabled; no scientific evaluation.</Description></RegistrationInfo>
  <Triggers><CalendarTrigger><StartBoundary>$nextBoundary</StartBoundary><Enabled>false</Enabled><ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay></CalendarTrigger></Triggers>
  <Principals><Principal id="Author"><UserId>$ownerSid</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>true</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>true</StopIfGoingOnBatteries><AllowHardTerminate>true</AllowHardTerminate><StartWhenAvailable>true</StartWhenAvailable><RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable><AllowStartOnDemand>false</AllowStartOnDemand><Enabled>false</Enabled><Hidden>true</Hidden><ExecutionTimeLimit>PT4H</ExecutionTimeLimit><Priority>7</Priority></Settings>
  <Actions Context="Author"><Exec><Command>$eShell</Command><Arguments>$eArgs</Arguments><WorkingDirectory>$eRepo</WorkingDirectory></Exec></Actions>
</Task>
"@
    [xml]$validated = $xml
    if ($validated.Task.Settings.Enabled -ne 'false' -or $validated.Task.Triggers.CalendarTrigger.Enabled -ne 'false') { throw 'XML_NOT_DISABLED' }
    $xmlPath = Join-Path $privateRoot 'task_disabled.xml'
    Write-NewUtf8 $xmlPath $xml
    $receipt = @{
        task_name = $taskName; status = 'PREPARED_DISABLED_XML_ONLY'; registration_attempted = (-not $PrepareOnly)
        config_sha256 = $configSha; xml_sha256 = (Get-FileHash -LiteralPath $xmlPath -Algorithm SHA256).Hash.ToLowerInvariant()
        data_root_created = $false; task_run_requested = $false; network_requests = 0; credential_reads = 0
    }
    if (-not $PrepareOnly) {
        try {
            $null = Register-ScheduledTask -TaskName $taskName -TaskPath '\' -Xml $xml -ErrorAction Stop
            $task = Get-ScheduledTask -TaskName $taskName -TaskPath '\' -ErrorAction Stop
            [xml]$actual = Export-ScheduledTask -TaskName $taskName -TaskPath '\'
            Write-NewUtf8 (Join-Path $privateRoot 'task_registered.xml') $actual.DocumentElement.OuterXml
            if ($task.State.ToString() -ne 'Disabled' -or $actual.Task.Settings.Enabled -ne 'false' -or
                $actual.Task.Triggers.CalendarTrigger.Enabled -ne 'false' -or
                $actual.Task.Actions.Exec.Command -ne $shellPath -or $actual.Task.Actions.Exec.Arguments -ne $actionArgs -or
                $actual.Task.Actions.Exec.WorkingDirectory -ne $RepoRoot) { throw 'REGISTERED_TASK_VALIDATION_FAILED' }
            $info = Get-ScheduledTaskInfo -TaskName $taskName -TaskPath '\'
            $receipt.status = 'CREATED_DISABLED_VERIFIED_NO_COLLECTION'
            $receipt.disabled = $true
            $receipt.last_run_time = $info.LastRunTime.ToString('o')
            $receipt.last_task_result = $info.LastTaskResult
        } catch {
            $receipt.status = 'NO_VERIFICABLE_NATIVE_REGISTRATION'
            $receipt.registration_error_type = $_.Exception.GetType().FullName
            $receipt.registration_hresult = $_.Exception.HResult
            $receipt.registration_error_id = $_.FullyQualifiedErrorId
        }
    }
    $after = TaskCensus
    Write-NewUtf8 (Join-Path $privateRoot 'other_tasks_after.json') ($after | ConvertTo-Json -Depth 8)
    $beforeCanonical = $before | ConvertTo-Json -Depth 8 -Compress
    $afterCanonical = $after | ConvertTo-Json -Depth 8 -Compress
    $receipt.other_task_count = $before.Count
    $receipt.other_task_definitions_unchanged = ($beforeCanonical -eq $afterCanonical)
    if (-not $receipt.other_task_definitions_unchanged) { throw 'OTHER_TASK_DEFINITIONS_CHANGED_DURING_SETUP' }
    if (Test-Path -LiteralPath $DataRoot) { throw 'DATA_ROOT_CREATED_DURING_DISABLED_SETUP' }
    Write-NewUtf8 (Join-Path $privateRoot 'setup_receipt.json') ($receipt | ConvertTo-Json -Depth 8)
    Write-Output ($receipt | ConvertTo-Json -Depth 8 -Compress)
    exit $(if ($receipt.status -eq 'NO_VERIFICABLE_NATIVE_REGISTRATION') { 2 } else { 0 })
} catch {
    Write-Output ('{"status":"SETUP_FAILED_NO_COLLECTION","error_type":"' + $_.Exception.GetType().Name + '","error_id":"' + $_.FullyQualifiedErrorId + '"}')
    exit 2
}
