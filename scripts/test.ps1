$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Python = "C:\Users\0yoyx\AppData\Local\Programs\Python\Python313\python.exe"

& $Python -m unittest discover -s tests
