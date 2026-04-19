# LLMOps First Demo

This project demonstrates a simple production-style LLMOps workflow for preparing a tuning dataset, automating Gemini supervised fine-tuning, and serving predictions with prompt and safety monitoring on Vertex AI.

## Pipeline

![Production pipeline diagram](./assets/pipeline-diagram.png)

```mermaid
flowchart TD
    A[L1.01_data.ipynb<br/>Prepare Stack Overflow Python QA data] --> B[Query BigQuery public dataset]
    B --> C[Add instruction template]
    C --> D[Split train and evaluation sets]
    D --> E[Export Gemini SFT JSONL files]

    E --> F[L2_automation.ipynb<br/>Automate tuning workflow]
    F --> G[Upload train and eval JSONL to GCS]
    G --> H[Start Vertex AI Gemini supervised tuning job]
    H --> I[Wait and monitor tuning job status]
    I --> J[Resolved tuned model and endpoint]

    J --> K[L3_predictions_prompts_safety.ipynb<br/>Online prediction and monitoring]
    K --> L[Load tuned endpoint from tuning job]
    L --> M[Build prompts with same training instruction format]
    M --> N[Generate predictions]
    N --> O[Capture monitoring signals]
    O --> P[Latency, finish reason, safety ratings, citations]
```

## Notebook Roles

- [L1.01_data.ipynb](./L1.01_data.ipynb) prepares the supervised fine-tuning dataset from the Stack Overflow BigQuery public dataset, adds the instruction prompt format, and exports training and evaluation JSONL files.
- [L2_automation.ipynb](./L2_automation.ipynb) automates the Gemini supervised fine-tuning workflow on Vertex AI and produces the tuned model resource plus the managed endpoint used for serving.
- [L3_predictions_prompts_safety.ipynb](./L3_predictions_prompts_safety.ipynb) loads the tuned deployment, sends production-style prompts, and records monitoring signals such as latency, safety results, finish reason, and citation metadata.

## Production Flow Summary

1. Data is prepared and versioned in `L1.01_data.ipynb`.
2. The tuning job is launched and tracked in `L2_automation.ipynb`.
3. The tuned model endpoint is used for prediction and monitoring in `L3_predictions_prompts_safety.ipynb`.
