param(
    [int]$Limit = 500,
    [double]$TestSize = 0.2,
    [string]$ApiBaseUrl = "http://localhost:5000/api",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath ".\.venv\Scripts\python.exe")) {
    throw "Project virtual environment not found at .\.venv. Run setup first."
}

$healthUrl = "$ApiBaseUrl/health"
$prepareUrl = "$ApiBaseUrl/data/prepare"

try {
    Invoke-RestMethod -Uri $healthUrl -Method Get | Out-Null
} catch {
    throw "Backend is not reachable at $ApiBaseUrl. Start it first with '.\.venv\Scripts\Activate.ps1' and 'python backend\app.py'."
}

$payload = @{
    limit = $Limit
    test_size = $TestSize
}

if ($OutputDir) {
    $payload.output_dir = $OutputDir
}

$jsonBody = $payload | ConvertTo-Json -Depth 4
$response = Invoke-RestMethod `
    -Uri $prepareUrl `
    -Method Post `
    -ContentType "application/json" `
    -Body $jsonBody

Write-Host ""
Write-Host "Data preparation complete." -ForegroundColor Green
Write-Host "Project ID: $($response.project_id)"
Write-Host "Total rows: $($response.row_count)"
Write-Host "Training rows: $($response.train_count)"
Write-Host "Evaluation rows: $($response.evaluation_count)"
Write-Host "Training file: $($response.training_data_file)"
Write-Host "Evaluation file: $($response.evaluation_data_file)"
