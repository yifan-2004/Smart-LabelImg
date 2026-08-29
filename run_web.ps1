param(
  [string]$Dataset = "",
  [int]$Port = 7860
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .\.venv-web\Scripts\python.exe)) {
  & .\setup_web.ps1
}
$arguments = @("-m", "smart_labelimg.web_app", "--port", "$Port")
if ($Dataset) { $arguments += @("--dataset", $Dataset) }
& .\.venv-web\Scripts\python.exe @arguments
if ($LASTEXITCODE -ne 0) { throw "Smart Label Web exited with code $LASTEXITCODE." }
