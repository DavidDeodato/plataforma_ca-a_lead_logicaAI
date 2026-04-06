$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot\..

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Ambiente virtual nao encontrado. Criando..."
    python -m venv .venv
}

Write-Host "Executando worker de follow-up..."
.\.venv\Scripts\python -m app.workers.followup_worker
