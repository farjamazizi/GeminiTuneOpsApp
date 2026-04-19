param(
    [Parameter(Mandatory = $true)]
    [string]$TuningJobResourceName,
    [string]$Region = "us-central1",
    [string]$ApiBaseUrl = "http://localhost:5000/api"
)

$ErrorActionPreference = "Stop"

$healthUrl = "$ApiBaseUrl/health"
$statusUrl = "$ApiBaseUrl/tuning/jobs/status?resource_name=$([uri]::EscapeDataString($TuningJobResourceName))&region=$([uri]::EscapeDataString($Region))"

try {
    Invoke-RestMethod -Uri $healthUrl -Method Get | Out-Null
} catch {
    throw "Backend is not reachable at $ApiBaseUrl. Start it first with '.\.venv\Scripts\activate.ps1' and 'python backend\app.py'."
}

$response = Invoke-RestMethod -Uri $statusUrl -Method Get

Write-Host ""
Write-Host "Tuning status fetched." -ForegroundColor Green
Write-Host "Resource: $($response.resource_name)"
Write-Host "State: $($response.state)"
Write-Host "Has ended: $($response.has_ended)"
Write-Host "Error: $($response.error)"
Write-Host "Tuned model: $($response.tuned_model_name)"
Write-Host "Tuned endpoint: $($response.tuned_model_endpoint_name)"
