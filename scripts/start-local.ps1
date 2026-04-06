$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot\..

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Ambiente virtual nao encontrado. Criando..."
    python -m venv .venv
}

Write-Host "Subindo API local em http://localhost:8000"
.\.venv\Scripts\python -m uvicorn app.main:app --reload
