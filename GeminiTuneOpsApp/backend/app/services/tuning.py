import time
from dataclasses import asdict, dataclass

import vertexai
from google.cloud import storage
from vertexai.tuning import sft

from .auth import authenticate


@dataclass
class TuningSubmissionResult:
    project_id: str
    region: str
    model_display_name: str
    source_model: str
    train_dataset_gcs_uri: str
    evaluation_dataset_gcs_uri: str
    tuning_job_resource_name: str
    tuning_job_state: str | None

    def to_dict(self) -> dict:
        return asdict(self)


def _parse_gcs_uri(gcs_uri: str) -> tuple[str, str]:
    if not gcs_uri.startswith("gs://"):
        raise ValueError("pipeline_root must start with gs://")
    bucket_and_prefix = gcs_uri.removeprefix("gs://")
    bucket_name, _, prefix = bucket_and_prefix.partition("/")
    return bucket_name, prefix.strip("/")


def upload_to_gcs(
    pipeline_root: str,
    local_path: str,
    destination_name: str,
    project_id: str,
    credentials: object,
) -> str:
    bucket_name, prefix = _parse_gcs_uri(pipeline_root)
    storage_client = storage.Client(project=project_id, credentials=credentials)
    bucket = storage_client.bucket(bucket_name)
    blob_name = f"{prefix}/{destination_name}" if prefix else destination_name
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(local_path)
    return f"gs://{bucket_name}/{blob_name}"


def submit_tuning_job(
    training_data_path: str,
    evaluation_data_path: str,
    pipeline_root: str,
    model_display_name: str,
    region: str,
    source_model: str,
) -> TuningSubmissionResult:
    credentials, project_id = authenticate()
    vertexai.init(project=project_id, location=region, credentials=credentials)

    train_dataset_gcs_uri = upload_to_gcs(
        pipeline_root,
        training_data_path,
        f"training/{model_display_name}.jsonl",
        project_id,
        credentials,
    )
    evaluation_dataset_gcs_uri = upload_to_gcs(
        pipeline_root,
        evaluation_data_path,
        f"validation/{model_display_name}.jsonl",
        project_id,
        credentials,
    )

    tuning_job = sft.train(
        source_model=source_model,
        train_dataset=train_dataset_gcs_uri,
        validation_dataset=evaluation_dataset_gcs_uri,
        tuned_model_display_name=model_display_name,
    )
    tuning_job.refresh()

    return TuningSubmissionResult(
        project_id=project_id,
        region=region,
        model_display_name=model_display_name,
        source_model=source_model,
        train_dataset_gcs_uri=train_dataset_gcs_uri,
        evaluation_dataset_gcs_uri=evaluation_dataset_gcs_uri,
        tuning_job_resource_name=tuning_job.resource_name,
        tuning_job_state=str(getattr(tuning_job, "state", None)),
    )


def get_tuning_job_status(
    tuning_job_resource_name: str,
    region: str,
    poll_seconds: int = 0,
) -> dict:
    credentials, project_id = authenticate()
    vertexai.init(project=project_id, location=region, credentials=credentials)

    tuning_job = sft.SupervisedTuningJob(tuning_job_resource_name)
    if poll_seconds > 0:
        time.sleep(poll_seconds)

    tuning_job.refresh()
    return {
        "project_id": project_id,
        "region": region,
        "resource_name": tuning_job.resource_name,
        "has_ended": tuning_job.has_ended,
        "state": str(getattr(tuning_job, "state", None)),
        "error": str(getattr(tuning_job, "error", None)),
        "tuned_model_name": getattr(tuning_job, "tuned_model_name", None),
        "tuned_model_endpoint_name": getattr(
            tuning_job, "tuned_model_endpoint_name", None
        ),
    }
