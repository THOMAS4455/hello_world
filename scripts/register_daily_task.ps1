<#
.SYNOPSIS
    Register (or remove) the Windows Task Scheduler fallback for daily live validation.

.DESCRIPTION
    The FastAPI app already schedules this job at 16:45 through APScheduler, but
    that only runs while the server is up. This task guarantees the validation
    runs once per weekday even when nobody starts the backend.

    Run this script yourself; the agent does not register system tasks, because
    scheduled tasks are a machine-level change.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts/register_daily_task.ps1
    powershell -ExecutionPolicy Bypass -File scripts/register_daily_task.ps1 -Remove
#>
[CmdletBinding()]
param(
    [string]$TaskName = "StockPrediction-LiveValidation",
    [string]$PythonPath,
    [switch]$Remove,
    [int]$Hour = 16,
    [int]$Minute = 45
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

if ($Remove) {
    schtasks /Delete /TN $TaskName /F
    Write-Host "Removed scheduled task '$TaskName'."
    exit $LASTEXITCODE
}

if (-not $PythonPath) {
    $venvPython = Join-Path $ProjectRoot ".venv/Scripts/python.exe"
    if (Test-Path $venvPython) {
        $PythonPath = $venvPython
    } else {
        $PythonPath = (Get-Command python).Source
    }
}

$script = Join-Path $ProjectRoot "scripts/daily_live_validation.py"
if (-not (Test-Path $script)) { throw "missing script: $script" }

# Build the command line without PowerShell escape characters so the task
# stores a literal quoted path pair.
$action = '"' + $PythonPath + '" "' + $script + '"'
$startTime = "{0:00}:{1:00}" -f $Hour, $Minute

schtasks /Create /TN $TaskName /TR $action /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST $startTime /F
Write-Host "Registered '$TaskName' -> $PythonPath $script (weekdays $startTime)."
Write-Output "Remove with: powershell -ExecutionPolicy Bypass -File scripts/register_daily_task.ps1 -Remove"
