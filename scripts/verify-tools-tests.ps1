# Gate pytest para tests/tools/ — Superpowers verification-before-completion
# Uso: .\scripts\verify-tools-tests.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    Write-Error "venv missing: $Py"
}
& $Py -m pytest tests/tools/ -v --tb=short
exit $LASTEXITCODE
