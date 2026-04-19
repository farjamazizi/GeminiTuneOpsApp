SHELL := powershell.exe
.SHELLFLAGS := -NoProfile -ExecutionPolicy Bypass -Command

PYTHON := .\.venv\Scripts\python.exe
PIP := $(PYTHON) -m pip
NPM := npm.cmd

LIMIT ?= 500
TEST_SIZE ?= 0.2
OUTPUT_DIR ?=

TRAINING_DATA_PATH ?=
EVALUATION_DATA_PATH ?=
PIPELINE_ROOT ?= gs://first-llmops-demo-bucket-2026/pipeline-root
SOURCE_MODEL ?= gemini-2.5-flash-lite
MODEL_DISPLAY_NAME ?=
REGION ?= us-central1
TUNING_JOB_RESOURCE ?=
TUNED_ENDPOINT ?=
QUESTION ?= How can I load a CSV file using pandas?

.PHONY: help install install-dev backend frontend-install frontend-dev prepare-data start-tuning check-tuning-status run-prediction

help:
	@Write-Host ""
	@Write-Host "GeminiTuneOpsApp Make Targets" -ForegroundColor Green
	@Write-Host "  make install               Install backend runtime dependencies"
	@Write-Host "  make install-dev           Install backend dev dependencies"
	@Write-Host "  make backend               Start Flask backend"
	@Write-Host "  make frontend-install      Install frontend dependencies"
	@Write-Host "  make frontend-dev          Start Vite frontend"
	@Write-Host "  make prepare-data          Run L1 data preparation"
	@Write-Host "  make start-tuning          Run L2 tuning submission"
	@Write-Host "  make check-tuning-status   Run L2 tuning status lookup"
	@Write-Host "  make run-prediction        Run L3 prediction"
	@Write-Host ""
	@Write-Host "Examples:" -ForegroundColor Yellow
	@Write-Host "  make prepare-data LIMIT=500 TEST_SIZE=0.2"
	@Write-Host "  make start-tuning TRAINING_DATA_PATH=...\ EVALUATION_DATA_PATH=..."
	@Write-Host "  make check-tuning-status TUNING_JOB_RESOURCE=projects/.../tuningJobs/..."
	@Write-Host "  make run-prediction TUNING_JOB_RESOURCE=projects/.../tuningJobs/... QUESTION=""How do I read a CSV with pandas?"""
	@Write-Host ""

install:
	$(PIP) install -r requirements.txt

install-dev:
	$(PIP) install -r requirements-dev.txt

backend:
	$(PYTHON) backend\app.py

frontend-install:
	cd frontend; $(NPM) install

frontend-dev:
	cd frontend; $(NPM) run dev

prepare-data:
	$$command = ".\scripts\prepare_data.ps1 -Limit $(LIMIT) -TestSize $(TEST_SIZE)"; \
	if ("$(OUTPUT_DIR)" -ne "") { $$command += " -OutputDir `"$(OUTPUT_DIR)`"" }; \
	Invoke-Expression $$command

start-tuning:
	if ("$(TRAINING_DATA_PATH)" -eq "") { throw "Set TRAINING_DATA_PATH=... when calling make start-tuning." }; \
	if ("$(EVALUATION_DATA_PATH)" -eq "") { throw "Set EVALUATION_DATA_PATH=... when calling make start-tuning." }; \
	$$command = ".\scripts\start_tuning.ps1 -TrainingDataPath `"$(TRAINING_DATA_PATH)`" -EvaluationDataPath `"$(EVALUATION_DATA_PATH)`" -PipelineRoot `"$(PIPELINE_ROOT)`" -SourceModel `"$(SOURCE_MODEL)`" -Region `"$(REGION)`""; \
	if ("$(MODEL_DISPLAY_NAME)" -ne "") { $$command += " -ModelDisplayName `"$(MODEL_DISPLAY_NAME)`"" }; \
	Invoke-Expression $$command

check-tuning-status:
	if ("$(TUNING_JOB_RESOURCE)" -eq "") { throw "Set TUNING_JOB_RESOURCE=projects/.../tuningJobs/... when calling make check-tuning-status." }; \
	.\scripts\check_tuning_status.ps1 -TuningJobResourceName "$(TUNING_JOB_RESOURCE)" -Region "$(REGION)"

run-prediction:
	$$hasJob = "$(TUNING_JOB_RESOURCE)" -ne ""; \
	$$hasEndpoint = "$(TUNED_ENDPOINT)" -ne ""; \
	if (-not $$hasJob -and -not $$hasEndpoint) { throw "Set either TUNING_JOB_RESOURCE=... or TUNED_ENDPOINT=... when calling make run-prediction." }; \
	$$command = ".\scripts\run_prediction.ps1 -Question `"$(QUESTION)`" -Region `"$(REGION)`""; \
	if ($$hasJob) { $$command += " -TuningJobResourceName `"$(TUNING_JOB_RESOURCE)`"" }; \
	if ($$hasEndpoint) { $$command += " -TunedModelEndpointName `"$(TUNED_ENDPOINT)`"" }; \
	Invoke-Expression $$command
