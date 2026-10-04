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

# Prefer the project virtualenv: it carries the pinned dependencies, including
# APScheduler. Without APScheduler the daily live-validation job is silently
# disabled by a try/except in src/jobs/investment_jobs.py.
$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
  $backendExe = $venvPython
  $backendArgs = @("app.py")
} else {
  $backendExe = "py"
  $backendArgs = @("-3", "app.py")
}

Start-Process -FilePath $backendExe -ArgumentList $backendArgs `
  -WorkingDirectory $ProjectRoot `
  -WindowStyle Hidden `
  -RedirectStandardOutput $backendOut `
  -RedirectStandardError $backendErr

# Node.js is frequently installed after this Windows session started. Windows does
# NOT propagate a new machine PATH to already-running processes (Explorer included),
# so npm can be missing here even though it works in a fresh terminal. Resolve it
# explicitly and extend PATH for the child process; otherwise the frontend window
# dies with a silent "npm is not recognized" and port 3000 never opens.
$npmDir = $null
$npmResolved = Get-Command npm.cmd -ErrorAction SilentlyContinue
if ($npmResolved) {
  $npmDir = Split-Path -Parent $npmResolved.Source
} else {
  $nodeCandidate = Join-Path $env:ProgramFiles "nodejs"
  if (Test-Path (Join-Path $nodeCandidate "npm.cmd")) { $npmDir = $nodeCandidate }
}
if ($npmDir -and ($env:PATH -notlike "*$npmDir*")) {
  $env:PATH = "$npmDir;$env:PATH"
}

if ($npmDir) {
  Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "set BROWSER=none&& set HOST=0.0.0.0&& npm start" `
    -WorkingDirectory (Join-Path $ProjectRoot "frontend") `
    -WindowStyle Hidden `
    -RedirectStandardOutput $frontendOut `
    -RedirectStandardError $frontendErr
} else {
  Write-Warning "npm not found; the frontend will NOT start. Install Node.js LTS with: winget install OpenJS.NodeJS.LTS"
}

Write-Output ("Backend  : {0} {1}" -f $backendExe, ($backendArgs -join " "))
Write-Output ("Frontend : " + $(if ($npmDir) { "npm start (node dir: $npmDir)" } else { "NOT STARTED (npm missing)" }))
Write-Output ("Backend logs:  {0}" -f $backendOut)
Write-Output ("Frontend logs: {0}" -f $frontendOut)
