param(
    [string]$TuningJobResourceName = "",
    [string]$TunedModelEndpointName = "",
    [string]$Question = "How can I load a CSV file using pandas?",
    [string]$PromptName = "single_prediction",
    [string]$Region = "us-central1",
    [double]$Temperature = 0.2,
    [int]$MaxOutputTokens = 512,
    [string]$ApiBaseUrl = "http://localhost:5000/api"
)

$ErrorActionPreference = "Stop"

if (-not $TuningJobResourceName -and -not $TunedModelEndpointName) {
    throw "Provide either -TuningJobResourceName or -TunedModelEndpointName."
}

$healthUrl = "$ApiBaseUrl/health"
$predictionUrl = "$ApiBaseUrl/predictions/generate"

try {
    Invoke-RestMethod -Uri $healthUrl -Method Get | Out-Null
} catch {
    throw "Backend is not reachable at $ApiBaseUrl. Start it first with '.\.venv\Scripts\activate.ps1' and 'python backend\app.py'."
}

$payload = @{
    question = $Question
    prompt_name = $PromptName
    region = $Region
    temperature = $Temperature
    max_output_tokens = $MaxOutputTokens
}

if ($TuningJobResourceName) {
    $payload.tuning_job_resource_name = $TuningJobResourceName
}

if ($TunedModelEndpointName) {
    $payload.tuned_model_endpoint_name = $TunedModelEndpointName
}

$jsonBody = $payload | ConvertTo-Json -Depth 5
$response = Invoke-RestMethod `
    -Uri $predictionUrl `
    -Method Post `
    -ContentType "application/json" `
    -Body $jsonBody

Write-Host ""
Write-Host "Prediction complete." -ForegroundColor Green
Write-Host "Endpoint: $($response.deployment.tuned_model_endpoint_name)"
if ($response.deployment.tuned_model_name) {
    Write-Host "Tuned model: $($response.deployment.tuned_model_name)"
}
Write-Host "Latency: $($response.prediction.latency_seconds)s"
Write-Host "Blocked: $($response.prediction.blocked)"
Write-Host "Finish reason: $($response.prediction.finish_reason)"
Write-Host ""
Write-Host "Answer:" -ForegroundColor Cyan
Write-Host $response.prediction.answer_text
