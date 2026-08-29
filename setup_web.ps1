param()
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$basePython = if (Get-Command py -ErrorAction SilentlyContinue) { @("py", "-3.11") } else { @("python") }
if ($basePython.Count -eq 2) {
  & $basePython[0] $basePython[1] -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)"
  & $basePython[0] $basePython[1] -m venv .venv-web
} else {
  & $basePython[0] -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)"
  if ($LASTEXITCODE -ne 0) { throw "Smart Label Web requires Python 3.11." }
  & $basePython[0] -m venv .venv-web
}
if ($LASTEXITCODE -ne 0) { throw "Failed to create .venv-web with Python 3.11." }

& .\.venv-web\Scripts\python.exe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade pip." }
& .\.venv-web\Scripts\python.exe -m pip install -r requirements-web.txt -r requirements-ai.txt
if ($LASTEXITCODE -ne 0) { throw "Failed to install local web dependencies." }
Write-Host "Setup complete. Run .\run_web.ps1"
