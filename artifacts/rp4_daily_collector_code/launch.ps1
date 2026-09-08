[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$ConfigPath,
    [Parameter(Mandatory)][string]$ConfigSha256,
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Set-PrivateDirectoryAcl([string]$Path, [string]$OwnerSid) {
    $acl = [System.Security.AccessControl.DirectorySecurity]::new()
    $acl.SetAccessRuleProtection($true, $false)
    $owner = [System.Security.Principal.SecurityIdentifier]::new($OwnerSid)
    $acl.SetOwner($owner)
    foreach ($sid in @($OwnerSid, 'S-1-5-18', 'S-1-5-32-544')) {
        $identity = [System.Security.Principal.SecurityIdentifier]::new($sid)
        $rule = [System.Security.AccessControl.FileSystemAccessRule]::new(
            $identity, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow'
        )
        $acl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $Path -AclObject $acl
}

function Assert-PrivateDirectoryAcl([string]$Path, [string]$OwnerSid) {
    $acl = Get-Acl -LiteralPath $Path
    if (-not $acl.AreAccessRulesProtected) { throw 'PRIVATE_ACL_INHERITANCE_NOT_PROTECTED' }
    $allowedSids = @($OwnerSid, 'S-1-5-18', 'S-1-5-32-544')
    foreach ($rule in $acl.Access) {
        $sid = $rule.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value
        if ($rule.AccessControlType -eq 'Allow' -and $sid -notin $allowedSids) {
            throw 'PRIVATE_ACL_UNEXPECTED_GRANT'
        }
    }
}

try {
    if ((Get-FileHash -LiteralPath $ConfigPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ConfigSha256) {
        throw 'CONFIG_HASH_MISMATCH'
    }
    $config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
    if ($config.task_name -ne 'OptionsVolatility-Daily-Collection') { throw 'TASK_IDENTITY_MISMATCH' }
    foreach ($pin in $config.source_sha256.PSObject.Properties) {
        $source = Join-Path $config.repo_root $pin.Name
        if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $pin.Value) {
            throw 'SOURCE_HASH_MISMATCH'
        }
    }
    $env:UV_PROJECT_ENVIRONMENT = $config.python_environment
    $env:PYTHONPATH = @($config.repo_root, (Join-Path $config.repo_root 'src'),
        (Join-Path $config.repo_root 'scripts'), (Join-Path $config.repo_root 'artifacts/rp4_code')) -join ';'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $env:PYTHONIOENCODING = 'utf-8'
    foreach ($name in @('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
        'NUMEXPR_NUM_THREADS', 'POLARS_MAX_THREADS')) {
        [Environment]::SetEnvironmentVariable($name, '2', 'Process')
    }
    Set-Location -LiteralPath $config.repo_root
    $arguments = @('run', '--offline', '--frozen', '--no-sync', 'python', '-B',
        'artifacts/rp4_daily_collector_code/collector.py', '--config', $ConfigPath,
        '--config-sha256', $ConfigSha256)
    if ($DryRun) {
        & $config.uv_path @arguments --dry-run
        exit $LASTEXITCODE
    }
    # This block is never reached by setup or dry-run. It only handles future collection.
    $rootPath = [IO.Path]::GetFullPath($config.data_root)
    $markerPath = Join-Path $rootPath 'collector_root.json'
    if (Test-Path -LiteralPath $rootPath) {
        $rootItem = Get-Item -LiteralPath $rootPath
        if ($rootItem.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'ROOT_REPARSE_REFUSED' }
        if (-not (Test-Path -LiteralPath $markerPath)) { throw 'ROOT_CONFLICT' }
        $marker = Get-Content -LiteralPath $markerPath -Raw | ConvertFrom-Json
        if ($marker.task_name -ne $config.task_name -or $marker.config_sha256 -ne $ConfigSha256) {
            throw 'ROOT_MARKER_MISMATCH'
        }
    } else {
        $null = [IO.Directory]::CreateDirectory($rootPath)
        Set-PrivateDirectoryAcl $rootPath $config.owner_sid
        $marker = @{ task_name = $config.task_name; config_sha256 = $ConfigSha256 } | ConvertTo-Json
        $bytes = [Text.Encoding]::UTF8.GetBytes($marker)
        $stream = [IO.File]::Open($markerPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write)
        try { $stream.Write($bytes, 0, $bytes.Length) } finally { $stream.Dispose() }
    }
    Assert-PrivateDirectoryAcl $rootPath $config.owner_sid
    # Only inherit already-existing provider variables; never read an env file or print values.
    foreach ($name in @('UNUSUALWHALES_API_KEY', 'FMP_API_KEY', 'MDS650_FMP_API_KEY')) {
        if (-not [Environment]::GetEnvironmentVariable($name, 'Process')) {
            $value = [Environment]::GetEnvironmentVariable($name, 'User')
            if (-not $value) { $value = [Environment]::GetEnvironmentVariable($name, 'Machine') }
            if ($value) { [Environment]::SetEnvironmentVariable($name, $value, 'Process') }
        }
    }
    $logDirectory = Join-Path $rootPath 'operations/launcher'
    $null = [IO.Directory]::CreateDirectory($logDirectory)
    $logPath = Join-Path $logDirectory ((Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffffffZ') + '.log')
    & $config.uv_path @arguments 2>&1 | Out-File -LiteralPath $logPath -Encoding utf8 -NoClobber
    exit $LASTEXITCODE
} catch {
    # No exception strings, request headers, URLs, machine paths or credentials reach stdout.
    Write-Output ('{"status":"LAUNCHER_FAILED","error_type":"' + $_.Exception.GetType().Name + '"}')
    exit 2
}
