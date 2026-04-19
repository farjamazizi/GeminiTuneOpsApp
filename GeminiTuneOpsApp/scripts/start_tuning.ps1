param(
    [Parameter(Mandatory = $true)]
    [string]$TrainingDataPath,

    [Parameter(Mandatory = $true)]
    [string]$EvaluationDataPath,

    [string]$PipelineRoot = "gs://first-llmops-demo-bucket-2026/pipeline-root",

    [string]$ModelDisplayName = "",
    [string]$SourceModel = "gemini-2.5-flash-lite",
    [string]$Region = "us-central1",
    [string]$ApiBaseUrl = "http://localhost:5000/api"
)

$ErrorActionPreference = "Stop"

$supportedModels = @(
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash"
)

if ($SourceModel -notin $supportedModels) {
    throw "SourceModel must be one of: $($supportedModels -join ', ')"
}

$healthUrl = "$ApiBaseUrl/health"
$tuningUrl = "$ApiBaseUrl/tuning/jobs"

try {
    Invoke-RestMethod -Uri $healthUrl -Method Get | Out-Null
} catch {
    throw "Backend is not reachable at $ApiBaseUrl. Start it first with '.\.venv\Scripts\activate.ps1' and 'python backend\app.py'."
}

if (-not (Test-Path -LiteralPath $TrainingDataPath)) {
    throw "TrainingDataPath not found: $TrainingDataPath"
}

if (-not (Test-Path -LiteralPath $EvaluationDataPath)) {
    throw "EvaluationDataPath not found: $EvaluationDataPath"
}

if (-not $ModelDisplayName) {
    $ModelDisplayName = "gemini-tune-ops-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
}

$payload = @{
    training_data_path = $TrainingDataPath
    evaluation_data_path = $EvaluationDataPath
    pipeline_root = $PipelineRoot
    model_display_name = $ModelDisplayName
    region = $Region
    source_model = $SourceModel
}

$jsonBody = $payload | ConvertTo-Json -Depth 5
$response = Invoke-RestMethod `
    -Uri $tuningUrl `
    -Method Post `
    -ContentType "application/json" `
    -Body $jsonBody

Write-Host ""
Write-Host "Tuning job submitted." -ForegroundColor Green
Write-Host "Model display name: $($response.model_display_name)"
Write-Host "Source model: $($response.source_model)"
Write-Host "Region: $($response.region)"
Write-Host "Train dataset GCS URI: $($response.train_dataset_gcs_uri)"
Write-Host "Evaluation dataset GCS URI: $($response.evaluation_dataset_gcs_uri)"
Write-Host "Tuning job resource: $($response.tuning_job_resource_name)"
Write-Host "Current state: $($response.tuning_job_state)"
