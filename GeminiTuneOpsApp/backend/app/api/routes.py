import datetime as dt
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from ..services.data_preparation import prepare_datasets
from ..services.prediction import (
    build_stackoverflow_prompt,
    predict_with_monitoring,
    resolve_deployed_model,
)
from ..services.tuning import get_tuning_job_status, submit_tuning_job


api_bp = Blueprint("api", __name__)


def _ensure_prompt(prompt_text: str | None) -> str:
    if not prompt_text:
        raise ValueError("Provide either question or prompt_text.")
    return prompt_text


def _get_json_payload(required: bool = False) -> dict:
    payload = request.get_json(silent=not required)
    if payload is None:
        if required:
            raise ValueError("Request body must be valid JSON.")
        return {}
    if not isinstance(payload, dict):
        raise ValueError("JSON request body must be an object.")
    return payload


def _validate_test_size(test_size: float) -> float:
    if not 0 < test_size < 1:
        raise ValueError("test_size must be greater than 0 and less than 1.")
    return test_size


def _validate_limit(limit: int) -> int:
    if limit <= 0:
        raise ValueError("limit must be greater than 0.")
    return limit


def _validate_source_model(source_model: str) -> str:
    supported_models = current_app.config["SUPPORTED_SOURCE_MODELS"]
    if source_model not in supported_models:
        raise ValueError(
            "source_model must be one of: "
            + ", ".join(supported_models)
        )
    return source_model


def _validate_pipeline_root(pipeline_root: str) -> str:
    if not pipeline_root.startswith("gs://"):
        raise ValueError("pipeline_root must start with gs://")
    if "your-bucket" in pipeline_root:
        raise ValueError(
            "pipeline_root still uses the placeholder bucket. "
            "Replace it with a real writable GCS path such as "
            "gs://YOUR_BUCKET/pipeline-root."
        )
    return pipeline_root


@api_bp.get("/health")
def health() -> tuple:
    return jsonify({"status": "ok", "service": "GeminiTuneOps backend"})


@api_bp.post("/data/prepare")
def prepare_data() -> tuple:
    payload = _get_json_payload()
    limit = _validate_limit(
        int(payload.get("limit", current_app.config["DEFAULT_QUERY_LIMIT"]))
    )
    test_size = _validate_test_size(
        float(payload.get("test_size", current_app.config["DEFAULT_EVAL_SPLIT"]))
    )
    output_dir = Path(
        payload.get("output_dir", current_app.config["DATA_DIR"] / "prepared")
    )

    result = prepare_datasets(
        output_dir=output_dir,
        limit=limit,
        test_size=test_size,
    )
    return jsonify(result.to_dict())


@api_bp.post("/tuning/jobs")
def create_tuning_job() -> tuple:
    payload = _get_json_payload(required=True)
    model_display_name = payload.get(
        "model_display_name",
        f"gemini-tune-ops-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}",
    )
    source_model = _validate_source_model(
        payload.get("source_model", current_app.config["DEFAULT_SOURCE_MODEL"])
    )
    pipeline_root = _validate_pipeline_root(
        payload.get("pipeline_root", current_app.config["DEFAULT_PIPELINE_ROOT"])
    )
    result = submit_tuning_job(
        training_data_path=payload["training_data_path"],
        evaluation_data_path=payload["evaluation_data_path"],
        pipeline_root=pipeline_root,
        model_display_name=model_display_name,
        region=payload.get("region", current_app.config["DEFAULT_REGION"]),
        source_model=source_model,
    )
    return jsonify(result.to_dict()), 201


@api_bp.get("/tuning/jobs/status")
def tuning_status() -> tuple:
    tuning_job_resource_name = request.args["resource_name"]
    region = request.args.get("region", current_app.config["DEFAULT_REGION"])
    poll_seconds = int(request.args.get("poll_seconds", 0))
    result = get_tuning_job_status(tuning_job_resource_name, region, poll_seconds)
    return jsonify(result)


@api_bp.post("/predictions/generate")
def generate_prediction() -> tuple:
    payload = _get_json_payload(required=True)
    region = payload.get("region", current_app.config["DEFAULT_REGION"])
    model, metadata = resolve_deployed_model(
        region=region,
        tuning_job_resource_name=payload.get("tuning_job_resource_name"),
        tuned_model_endpoint_name=payload.get("tuned_model_endpoint_name"),
    )

    question = payload.get("question")
    prompt_text = payload.get("prompt_text")
    if question and not prompt_text:
        prompt_text = build_stackoverflow_prompt(question)
    prompt_text = _ensure_prompt(prompt_text)

    record = predict_with_monitoring(
        model=model,
        prompt_name=payload.get("prompt_name", "single_prediction"),
        prompt_text=prompt_text,
        temperature=float(
            payload.get("temperature", current_app.config["DEFAULT_TEMPERATURE"])
        ),
        max_output_tokens=int(
            payload.get(
                "max_output_tokens", current_app.config["DEFAULT_MAX_OUTPUT_TOKENS"]
            )
        ),
    )
    return jsonify({"deployment": metadata, "prediction": record.to_dict()})


@api_bp.post("/predictions/monitor")
def monitor_predictions() -> tuple:
    payload = _get_json_payload(required=True)
    region = payload.get("region", current_app.config["DEFAULT_REGION"])
    model, metadata = resolve_deployed_model(
        region=region,
        tuning_job_resource_name=payload.get("tuning_job_resource_name"),
        tuned_model_endpoint_name=payload.get("tuned_model_endpoint_name"),
    )

    prompts = payload.get("prompts", [])
    if not isinstance(prompts, list) or not prompts:
        raise ValueError("prompts must be a non-empty array.")

    records = []
    for item in prompts:
        if not isinstance(item, dict):
            raise ValueError("Each prompt entry must be an object.")
        prompt_text = item.get("prompt_text")
        question = item.get("question")
        if question and not prompt_text:
            prompt_text = build_stackoverflow_prompt(question)
        prompt_text = _ensure_prompt(prompt_text)

        record = predict_with_monitoring(
            model=model,
            prompt_name=item.get("prompt_name", "unnamed_prompt"),
            prompt_text=prompt_text,
            temperature=float(
                item.get("temperature", current_app.config["DEFAULT_TEMPERATURE"])
            ),
            max_output_tokens=int(
                item.get(
                    "max_output_tokens",
                    current_app.config["DEFAULT_MAX_OUTPUT_TOKENS"],
                )
            ),
        )
        records.append(record.to_dict())

    return jsonify({"deployment": metadata, "records": records})
