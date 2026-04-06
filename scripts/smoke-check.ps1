$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot\..

Write-Host "Health:"
Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get | ConvertTo-Json -Depth 5

Write-Host "`nReadiness:"
Invoke-RestMethod -Uri "http://localhost:8000/api/readiness" -Method Get | ConvertTo-Json -Depth 5
