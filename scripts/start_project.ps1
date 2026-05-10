$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$LogsRoot = Join-Path $ProjectRoot "logs"
$BackendLogs = Join-Path $LogsRoot "backend"
$FrontendLogs = Join-Path $LogsRoot "frontend"
$ArchiveLogs = Join-Path $LogsRoot "root_archive"

New-Item -ItemType Directory -Force -Path $BackendLogs | Out-Null
New-Item -ItemType Directory -Force -Path $FrontendLogs | Out-Null
New-Item -ItemType Directory -Force -Path $ArchiveLogs | Out-Null

# Move misplaced root logs into archive before start.
Get-ChildItem -Path $ProjectRoot -File |
  Where-Object { $_.Extension -in ".log", ".out", ".err" } |
  ForEach-Object {
    $dst = Join-Path $ArchiveLogs $_.Name
    if (Test-Path $dst) {
      $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
      $dst = Join-Path $ArchiveLogs ("{0}_{1}{2}" -f $_.BaseName, $stamp, $_.Extension)
    }
    Move-Item -LiteralPath $_.FullName -Destination $dst -Force
  }

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$backendOut = Join-Path $BackendLogs ("backend_{0}.out.log" -f $ts)
$backendErr = Join-Path $BackendLogs ("backend_{0}.err.log" -f $ts)
$frontendOut = Join-Path $FrontendLogs ("frontend_{0}.out.log" -f $ts)
$frontendErr = Join-Path $FrontendLogs ("frontend_{0}.err.log" -f $ts)

Start-Process -FilePath "py" -ArgumentList "-3", "app.py" `
  -WorkingDirectory $ProjectRoot `
  -WindowStyle Hidden `
  -RedirectStandardOutput $backendOut `
  -RedirectStandardError $backendErr

Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm start" `
  -WorkingDirectory (Join-Path $ProjectRoot "frontend") `
  -WindowStyle Hidden `
  -RedirectStandardOutput $frontendOut `
  -RedirectStandardError $frontendErr

Write-Output "Started backend and frontend."
Write-Output ("Backend logs:  {0}" -f $backendOut)
Write-Output ("Frontend logs: {0}" -f $frontendOut)
