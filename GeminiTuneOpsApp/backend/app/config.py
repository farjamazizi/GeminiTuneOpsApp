from pathlib import Path


class Config:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    DATA_DIR = PROJECT_ROOT / "data"
    DEFAULT_REGION = "us-central1"
    DEFAULT_SOURCE_MODEL = "gemini-2.5-flash-lite"
    DEFAULT_PIPELINE_ROOT = "gs://first-llmops-demo-bucket-2026/pipeline-root"
    SUPPORTED_SOURCE_MODELS = (
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
    )
    DEFAULT_QUERY_LIMIT = 500
    DEFAULT_EVAL_SPLIT = 0.2
    DEFAULT_TEMPERATURE = 0.2
    DEFAULT_MAX_OUTPUT_TOKENS = 512
