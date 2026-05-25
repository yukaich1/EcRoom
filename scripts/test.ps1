$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$PythonCandidates = @(
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe",
    "python"
)

$Python = $PythonCandidates | Where-Object {
    if ($_ -eq "python") { return $true }
    Test-Path $_
} | Select-Object -First 1

& $Python -m unittest discover -s tests
