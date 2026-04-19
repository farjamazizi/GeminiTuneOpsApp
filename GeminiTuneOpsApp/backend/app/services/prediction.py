import html
import re
import time
from dataclasses import asdict, dataclass
from html.parser import HTMLParser

import vertexai
from vertexai.generative_models import GenerationConfig, GenerativeModel
from vertexai.tuning import sft

from .auth import authenticate
from .data_preparation import INSTRUCTION_TEMPLATE


@dataclass
class MonitoringRecord:
    prompt_name: str
    prompt_text: str
    answer_text: str
    raw_answer_text: str
    latency_seconds: float
    blocked: bool
    finish_reason: str | None
    safety_ratings: list[dict]
    citation_count: int
    usage_metadata: dict

    def to_dict(self) -> dict:
        return asdict(self)


def _serialize_usage_metadata(usage_metadata: object) -> dict:
    if usage_metadata is None:
        return {}

    result = {}
    for field in (
        "prompt_token_count",
        "candidates_token_count",
        "total_token_count",
        "cached_content_token_count",
    ):
        value = getattr(usage_metadata, field, None)
        if value is not None:
            result[field] = value
    return result


def _serialize_safety_ratings(candidate: object) -> list[dict]:
    ratings = list(getattr(candidate, "safety_ratings", []) or [])
    return [
        {
            "category": str(getattr(rating, "category", "")),
            "probability": str(getattr(rating, "probability", "")),
            "probability_score": getattr(rating, "probability_score", None),
            "severity": str(getattr(rating, "severity", "")),
            "severity_score": getattr(rating, "severity_score", None),
            "blocked": getattr(rating, "blocked", None),
        }
        for rating in ratings
    ]


class _HtmlToTextFormatter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.list_stack: list[str] = []
        self.in_pre = False
        self.in_code = False
        self.href: str | None = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "p":
            self._ensure_block_break()
        elif tag == "br":
            self.parts.append("\n")
        elif tag == "pre":
            self._ensure_block_break()
            self.in_pre = True
            self.parts.append("```python\n")
        elif tag == "code" and not self.in_pre:
            self.in_code = True
            self.parts.append("`")
        elif tag in {"ul", "ol"}:
            self._ensure_block_break()
            self.list_stack.append(tag)
        elif tag == "li":
            indent = "  " * max(len(self.list_stack) - 1, 0)
            bullet = "- " if (not self.list_stack or self.list_stack[-1] == "ul") else "1. "
            self.parts.append(f"\n{indent}{bullet}")
        elif tag == "blockquote":
            self._ensure_block_break()
            self.parts.append("> ")
        elif tag == "a":
            self.href = attrs_dict.get("href")

    def handle_endtag(self, tag):
        if tag == "p":
            self.parts.append("\n\n")
        elif tag == "pre":
            self.in_pre = False
            self.parts.append("\n```\n\n")
        elif tag == "code" and not self.in_pre:
            self.parts.append("`")
            self.in_code = False
        elif tag in {"ul", "ol"} and self.list_stack:
            self.list_stack.pop()
            self.parts.append("\n")
        elif tag == "blockquote":
            self.parts.append("\n\n")
        elif tag == "a" and self.href:
            self.parts.append(f" ({self.href})")
            self.href = None

    def handle_data(self, data):
        if not data:
            return
        text = html.unescape(data)
        if self.in_pre:
            self.parts.append(text)
            return
        collapsed = re.sub(r"\s+", " ", text)
        self.parts.append(collapsed)

    def get_text(self) -> str:
        text = "".join(self.parts)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+\n", "\n", text)
        return text.strip()

    def _ensure_block_break(self):
        if self.parts and not self.parts[-1].endswith("\n\n"):
            self.parts.append("\n\n")


def normalize_answer_text(answer_text: str) -> str:
    if not answer_text:
        return ""

    if "<" not in answer_text or ">" not in answer_text:
        return answer_text.strip()

    formatter = _HtmlToTextFormatter()
    formatter.feed(answer_text)
    normalized = formatter.get_text()
    if normalized:
        return normalized

    # Fallback in case the parser produced nothing useful.
    return html.unescape(re.sub(r"<[^>]+>", "", answer_text)).strip()


def build_stackoverflow_prompt(question: str) -> str:
    format_instruction = (
        "\n\nPlease answer in clear plain text or Markdown. "
        "Do not use HTML tags such as <p>, <pre>, <code>, or <a>."
    )
    return f"{INSTRUCTION_TEMPLATE}{question}{format_instruction}"


def resolve_deployed_model(
    region: str,
    tuning_job_resource_name: str | None,
    tuned_model_endpoint_name: str | None,
) -> tuple[GenerativeModel, dict]:
    credentials, project_id = authenticate()
    vertexai.init(project=project_id, location=region, credentials=credentials)

    tuned_model_name = None
    if tuning_job_resource_name:
        tuning_job = sft.SupervisedTuningJob(tuning_job_resource_name)
        tuning_job.refresh()
        if not tuning_job.has_ended:
            raise ValueError("The tuning job has not finished yet.")
        tuned_model_name = getattr(tuning_job, "tuned_model_name", None)
        tuned_model_endpoint_name = getattr(
            tuning_job, "tuned_model_endpoint_name", tuned_model_endpoint_name
        )

    if not tuned_model_endpoint_name:
        raise ValueError(
            "A tuned_model_endpoint_name or finished tuning_job_resource_name is required."
        )

    model = GenerativeModel(tuned_model_endpoint_name)
    metadata = {
        "project_id": project_id,
        "region": region,
        "tuned_model_name": tuned_model_name,
        "tuned_model_endpoint_name": tuned_model_endpoint_name,
    }
    return model, metadata


def predict_with_monitoring(
    model: GenerativeModel,
    prompt_name: str,
    prompt_text: str,
    temperature: float,
    max_output_tokens: int,
) -> MonitoringRecord:
    start = time.perf_counter()
    response = model.generate_content(
        prompt_text,
        generation_config=GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        ),
    )
    latency_seconds = round(time.perf_counter() - start, 2)

    candidate = response.candidates[0] if getattr(response, "candidates", None) else None
    citations = list(
        getattr(getattr(candidate, "citation_metadata", None), "citations", []) or []
    )
    safety_ratings = _serialize_safety_ratings(candidate)
    blocked = any(rating.get("blocked") for rating in safety_ratings)
    raw_answer_text = response.text
    answer_text = normalize_answer_text(raw_answer_text)

    return MonitoringRecord(
        prompt_name=prompt_name,
        prompt_text=prompt_text,
        answer_text=answer_text,
        raw_answer_text=raw_answer_text,
        latency_seconds=latency_seconds,
        blocked=blocked,
        finish_reason=str(getattr(candidate, "finish_reason", None)),
        safety_ratings=safety_ratings,
        citation_count=len(citations),
        usage_metadata=_serialize_usage_metadata(
            getattr(response, "usage_metadata", None)
        ),
    )
