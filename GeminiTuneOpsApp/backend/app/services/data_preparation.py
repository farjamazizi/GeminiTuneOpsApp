import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd
from google.cloud import bigquery
from sklearn.model_selection import train_test_split

from .auth import authenticate


INSTRUCTION_TEMPLATE = """Please answer the following Stackoverflow question on Python. Answer it like you are a developer answering Stackoverflow questions.

Stackoverflow question:
"""


@dataclass
class DataPreparationResult:
    project_id: str
    row_count: int
    train_count: int
    evaluation_count: int
    training_data_file: str
    evaluation_data_file: str
    instruction_template: str

    def to_dict(self) -> dict:
        return asdict(self)


def build_training_query(limit: int) -> str:
    return f"""
SELECT
    CONCAT(q.title, q.body) AS input_text,
    a.body AS output_text
FROM
    `bigquery-public-data.stackoverflow.posts_questions` q
JOIN
    `bigquery-public-data.stackoverflow.posts_answers` a
ON
    q.accepted_answer_id = a.id
WHERE
    q.accepted_answer_id IS NOT NULL
    AND REGEXP_CONTAINS(q.tags, "python")
    AND a.creation_date >= "2020-01-01"
LIMIT {int(limit)}
""".strip()


def to_gemini_sft_jsonl(df: pd.DataFrame) -> str:
    lines = []
    for _, row in df.iterrows():
        example = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": row["input_text_instruct"]}],
                },
                {
                    "role": "model",
                    "parts": [{"text": row["output_text"]}],
                },
            ]
        }
        lines.append(json.dumps(example, ensure_ascii=False))
    return "\n".join(lines)


def prepare_datasets(
    output_dir: Path,
    limit: int,
    test_size: float,
    random_state: int = 42,
) -> DataPreparationResult:
    credentials, project_id = authenticate()
    bq_client = bigquery.Client(project=project_id, credentials=credentials)

    query = build_training_query(limit)
    stack_overflow_df = bq_client.query(query).result().to_arrow().to_pandas()
    stack_overflow_df["input_text_instruct"] = (
        INSTRUCTION_TEMPLATE + stack_overflow_df["input_text"]
    )

    train_df, evaluation_df = train_test_split(
        stack_overflow_df,
        test_size=test_size,
        random_state=random_state,
    )

    timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir.mkdir(parents=True, exist_ok=True)

    training_path = output_dir / f"tune_data_stack_overflow_gemini_python_qa-{timestamp}.jsonl"
    evaluation_path = output_dir / (
        f"tune_eval_data_stack_overflow_gemini_python_qa-{timestamp}.jsonl"
    )

    training_path.write_text(to_gemini_sft_jsonl(train_df), encoding="utf-8")
    evaluation_payload = to_gemini_sft_jsonl(evaluation_df)
    evaluation_path.write_text(evaluation_payload, encoding="utf-8")

    return DataPreparationResult(
        project_id=project_id,
        row_count=len(stack_overflow_df),
        train_count=len(train_df),
        evaluation_count=len(evaluation_df),
        training_data_file=str(training_path),
        evaluation_data_file=str(evaluation_path),
        instruction_template=INSTRUCTION_TEMPLATE,
    )
