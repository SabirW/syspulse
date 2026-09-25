<#
.SYNOPSIS
    Collects a snapshot of local system health (disks, key services, recent
    error events) and writes it as JSON for SysPulse to analyze.

.DESCRIPTION
    Designed to run on a Windows workstation or server, on a schedule
    (Task Scheduler / cron via pwsh) or ad hoc during a support call.
    It only reads system state — it never changes anything.

.PARAMETER Services
    Names of Windows services to check (as shown by Get-Service -Name).
    Defaults to a small set of services that commonly cause support tickets
    when they stop unexpectedly.

.PARAMETER ErrorLookbackHours
    How far back to look in the Application and System event logs for
    Error/Critical entries. Default: 24 hours.

.PARAMETER OutFile
    If set, writes the JSON report to this path instead of stdout.

.EXAMPLE
    pwsh ./collect_windows.ps1 -OutFile report.json

.EXAMPLE
    pwsh ./collect_windows.ps1 -Services "Spooler","wuauserv" -ErrorLookbackHours 12
#>

[CmdletBinding()]
param(
    [string[]] $Services = @("Spooler", "wuauserv", "BITS", "WinDefend"),
    [int] $ErrorLookbackHours = 24,
    [string] $OutFile
)

$ErrorActionPreference = "Stop"

function Get-DiskSnapshot {
    Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
        $totalGb = [math]::Round($_.Size / 1GB, 1)
        $freeGb  = [math]::Round($_.FreeSpace / 1GB, 1)
        $freePct = if ($_.Size -gt 0) { [math]::Round(($_.FreeSpace / $_.Size) * 100, 1) } else { 0 }
        [PSCustomObject]@{
            drive     = $_.DeviceID
            total_gb  = $totalGb
            free_gb   = $freeGb
            free_pct  = $freePct
        }
    }
}

function Get-ServiceSnapshot {
    param([string[]] $Names)

    foreach ($name in $Names) {
        $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
        if (-not $svc) {
            [PSCustomObject]@{
                name         = $name
                display_name = $null
                status       = "NotFound"
                start_type   = $null
            }
            continue
        }
        [PSCustomObject]@{
            name         = $svc.Name
            display_name = $svc.DisplayName
            status       = $svc.Status.ToString()
            start_type   = $svc.StartType.ToString()
        }
    }
}

function Get-RecentErrorEvents {
    param([int] $LookbackHours)

    $startTime = (Get-Date).AddHours(-$LookbackHours)
    $filter = @{
        LogName   = "Application", "System"
        Level     = 1, 2   # Critical, Error
        StartTime = $startTime
    }

    try {
        Get-WinEvent -FilterHashtable $filter -ErrorAction Stop |
            Select-Object -First 50 |
            ForEach-Object {
                [PSCustomObject]@{
                    time    = $_.TimeCreated.ToUniversalTime().ToString("o")
                    log     = $_.LogName
                    source  = $_.ProviderName
                    id      = $_.Id
                    message = ($_.Message -split "`n")[0]
                }
            }
    }
    catch [Exception] {
        # No matching events is the common case and throws in Get-WinEvent;
        # anything else is worth surfacing rather than swallowing silently.
        if ($_.Exception.Message -notmatch "No events were found") {
            Write-Warning "Could not read event log: $($_.Exception.Message)"
        }
        @()
    }
}

$report = [ordered]@{
    hostname      = $env:COMPUTERNAME
    collected_at  = (Get-Date).ToUniversalTime().ToString("o")
    disks         = @(Get-DiskSnapshot)
    services      = @(Get-ServiceSnapshot -Names $Services)
    recent_errors = @(Get-RecentErrorEvents -LookbackHours $ErrorLookbackHours)
}

$json = $report | ConvertTo-Json -Depth 5

if ($OutFile) {
    $json | Out-File -FilePath $OutFile -Encoding utf8
    Write-Host "Report written to $OutFile"
} else {
    Write-Output $json
}
