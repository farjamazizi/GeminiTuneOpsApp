# GeminiTuneOpsApp

`GeminiTuneOpsApp` packages the notebook workflow from `L1.01_data.ipynb`, `L2_automation.ipynb`, and `L3_predictions_prompts_safety.ipynb` into a production-style application with a Flask backend and a React frontend.

## What it contains

- `backend/` exposes API endpoints for dataset preparation, supervised tuning orchestration, tuning-status lookup, and monitored predictions.
- `frontend/` provides a simplified Q&A workspace for pasting a tuning job resource, asking a question, and reading the tuned answer.
- `scripts/` contains PowerShell helpers for the L1, L2, and L3 flow.
- `requirements.txt` contains the Python runtime dependencies for the Flask backend.
- `requirements-dev.txt` extends runtime dependencies with notebook and development tooling.
- `CICD_ROADMAP.md` lays out a practical path from local development to production delivery.

## Demo Video

[Demo Video](./assets/demo.mp4)

## L1 to L3 mapping

- `L1.01_data.ipynb` -> `backend/app/services/data_preparation.py`
- `L2_automation.ipynb` -> `backend/app/services/tuning.py`
- `L3_predictions_prompts_safety.ipynb` -> `backend/app/services/prediction.py`

## Backend API

- `GET /api/health`
- `POST /api/data/prepare`
- `POST /api/tuning/jobs`
- `GET /api/tuning/jobs/status`
- `POST /api/predictions/generate`
- `POST /api/predictions/monitor`

## Quick Start

### Backend

```powershell
cd c:\llmops-first-demo\GeminiTuneOpsApp
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python backend\app.py
```

### Backend with development tools

Use this when you want notebook support, linting, and tests in the same environment.

```powershell
cd c:\llmops-first-demo\GeminiTuneOpsApp
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

## Workflow

### 1. Prepare Data

Start the backend first, then run the helper from the app root.

```powershell
cd c:\llmops-first-demo\GeminiTuneOpsApp
.\.venv\Scripts\Activate.ps1
python backend\app.py
```

In another terminal:

```powershell
cd c:\llmops-first-demo\GeminiTuneOpsApp
.\scripts\prepare_data.ps1 -Limit 500 -TestSize 0.2
```

Optional custom output directory:

```powershell
.\scripts\prepare_data.ps1 -Limit 500 -TestSize 0.2 -OutputDir "c:\llmops-first-demo\GeminiTuneOpsApp\data\custom"
```

Prepared files are written under `GeminiTuneOpsApp\data\prepared`.

### 2. Start Tuning

After data preparation, submit a tuning job with the prepared train and evaluation files.

```powershell
cd c:\llmops-first-demo\GeminiTuneOpsApp
.\scripts\start_tuning.ps1 `
  -TrainingDataPath "c:\llmops-first-demo\GeminiTuneOpsApp\data\prepared\tune_data_stack_overflow_gemini_python_qa-YYYY-MM-DD_HH-MM-SS.jsonl" `
  -EvaluationDataPath "c:\llmops-first-demo\GeminiTuneOpsApp\data\prepared\tune_eval_data_stack_overflow_gemini_python_qa-YYYY-MM-DD_HH-MM-SS.jsonl" `
  -PipelineRoot "gs://first-llmops-demo-bucket-2026/pipeline-root" `
  -SourceModel "gemini-2.5-flash-lite"
```

If you omit `-PipelineRoot`, the app now defaults to:

```text
gs://first-llmops-demo-bucket-2026/pipeline-root
```

Supported source models in the current app:

- `gemini-2.5-flash-lite`
- `gemini-2.5-flash`

Default pipeline root:

```text
gs://first-llmops-demo-bucket-2026/pipeline-root
```

### 3. Check Tuning Status

```powershell
cd c:\llmops-first-demo\GeminiTuneOpsApp
.\scripts\check_tuning_status.ps1 `
  -TuningJobResourceName "projects/YOUR_PROJECT/locations/us-central1/tuningJobs/YOUR_TUNING_JOB_ID"
```

### 4. Run A Prediction

Use either the finished tuning job resource or the tuned endpoint directly.

```powershell
cd c:\llmops-first-demo\GeminiTuneOpsApp
.\scripts\run_prediction.ps1 `
  -TuningJobResourceName "projects/YOUR_PROJECT/locations/us-central1/tuningJobs/YOUR_TUNING_JOB_ID" `
  -Question "How can I load a CSV file using pandas?"
```

Or with the tuned endpoint:

```powershell
.\scripts\run_prediction.ps1 `
  -TunedModelEndpointName "projects/YOUR_PROJECT/locations/us-central1/endpoints/YOUR_ENDPOINT_ID" `
  -Question "How can I load a CSV file using pandas?"
```

The backend now normalizes model output into clearer plain text or Markdown-like answers and keeps raw model output only as an optional debugging view.

### Frontend

```powershell
cd c:\llmops-first-demo\GeminiTuneOpsApp\frontend
npm install
npm run dev
```

When the frontend is running, the main page is intentionally simple:

1. Paste a finished tuning job resource.
2. Type a Python question.
3. Click `Ask Model`.
4. Read the tuned answer in the answer panel.

The current frontend design is focused on the L3 prediction experience rather than the full operations control plane.

## Example Resource

If you want to test the frontend with the resource used during development, paste:

```text
projects/838831985868/locations/us-central1/tuningJobs/4018836890693140480
```

## Notes

- The backend expects Google Cloud credentials and a valid project configuration.
- `requirements.txt` is the production/runtime dependency set for the Flask backend.
- `requirements-dev.txt` extends the runtime set with development and notebook tooling.
- Tuning submission requires a writable `gs://` bucket path in `pipeline_root`.
- Tuning submission currently validates `source_model` against the app-supported allowlist.
- The prediction routes can resolve the tuned endpoint from a completed tuning job resource, or you can pass the endpoint directly.
- Node.js and `npm` are required separately for the React frontend.
- If PowerShell cannot find `npm`, try `npm.cmd` or open a new terminal after installing Node.js.
