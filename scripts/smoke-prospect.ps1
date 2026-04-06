$ErrorActionPreference = "Stop"

param(
    [string]$Niche = "barbearia",
    [string]$City = "Vitoria, ES",
    [int]$Limit = 1
)

Set-Location $PSScriptRoot\..

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Ambiente virtual nao encontrado. Criando..."
    python -m venv .venv
}

Write-Host "Rodando smoke real de prospeccao..."
.\.venv\Scripts\python -c "from fastapi.testclient import TestClient; from app.main import app; client=TestClient(app); resp=client.post('/api/prospecting/run', json={'niche':'$Niche','city':'$City','limit':$Limit,'enrich':True}); print(resp.status_code); print(resp.json())"
