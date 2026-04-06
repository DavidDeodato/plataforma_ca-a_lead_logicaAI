$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot\..\frontend

if (-not (Test-Path ".\node_modules")) {
    Write-Host "Dependencias do frontend nao encontradas. Instalando..."
    npm install
}

if (-not (Test-Path ".\.env")) {
    Copy-Item ".\.env.example" ".\.env"
}

Write-Host "Subindo frontend React em http://127.0.0.1:5173"
npm run dev
