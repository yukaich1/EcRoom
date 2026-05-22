$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$PythonCandidates = @(
    "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "python"
)

$Python = $PythonCandidates | Where-Object {
    if ($_ -eq "python") { return $true }
    Test-Path $_
} | Select-Object -First 1

& $Python -m evolving_creative_room.web --host 127.0.0.1 --port 8765
