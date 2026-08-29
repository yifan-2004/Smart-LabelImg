param(
  [switch]$SkipAi,
  [switch]$Build
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Invoke-BasePython {
  param([string[]]$Arguments)

  if ($env:PYTHON_BIN) {
    & $env:PYTHON_BIN @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Python command failed with exit code $LASTEXITCODE." }
    return
  }
  if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3.11 @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Python command failed with exit code $LASTEXITCODE." }
    return
  }
  if (Get-Command python -ErrorAction SilentlyContinue) {
    & python @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Python command failed with exit code $LASTEXITCODE." }
    return
  }
  throw "Python 3.11 is required. Install it from https://www.python.org/downloads/windows/ and run this script again."
}

if (-not (Test-Path .\.venv\Scripts\python.exe)) {
  Invoke-BasePython -Arguments @("-m", "venv", ".venv")
}

$venvPython = ".\.venv\Scripts\python.exe"
& $venvPython -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)"
if ($LASTEXITCODE -ne 0) {
  throw ".venv must use Python 3.11. Remove .venv, install Python 3.11, and run this script again."
}
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade pip." }
& $venvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Failed to install requirements.txt." }

if (-not $SkipAi) {
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is required to install MobileSAM from requirements-ai.txt. Install Git for Windows, or rerun with -SkipAi for UI-only development."
  }
  & $venvPython -m pip install -r requirements-ai.txt
  if ($LASTEXITCODE -ne 0) { throw "Failed to install requirements-ai.txt." }
}

if ($Build) {
  & $venvPython -m pip install -r requirements-build.txt
  if ($LASTEXITCODE -ne 0) { throw "Failed to install requirements-build.txt." }
}

Write-Host "Setup complete."
Write-Host "Run .\run.ps1 to start Smart LabelImg from source."
Write-Host "Run .\build_app.ps1 to build the Windows release package."
