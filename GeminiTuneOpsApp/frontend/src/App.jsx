import { useState } from "react";
import { generatePrediction } from "./api";

function ResultSummary({ results }) {
  const summaryRows = [
    results.prediction
      ? `Single prediction latency: ${results.prediction.prediction.latency_seconds}s.`
      : null,
  ].filter(Boolean);

  if (!summaryRows.length && !results.error) {
    return (
      <div className="empty-state">
        Run a workflow step to see data prep, tuning, and prediction results here.
      </div>
    );
  }

  return (
    <div className="summary-stack">
      {results.error ? <div className="error">{results.error}</div> : null}
      {summaryRows.map((row) => (
        <div className="summary-pill" key={row}>
          {row}
        </div>
      ))}
    </div>
  );
}

function App() {
  const [predictionForm, setPredictionForm] = useState({
    tuning_job_resource_name:
      "projects/838831985868/locations/us-central1/tuningJobs/4018836890693140480",
    question: "How can I load a CSV file using pandas?",
    prompt_name: "single_prediction",
    region: "us-central1",
  });
  const [results, setResults] = useState({
    prediction: null,
    error: null,
  });
  const [loading, setLoading] = useState("");

  async function runAction(actionName, action) {
    setLoading(actionName);
    setResults((prev) => ({ ...prev, error: null }));
    try {
      const payload = await action();
      return payload;
    } catch (error) {
      setResults((prev) => ({ ...prev, error: error.message }));
      throw error;
    } finally {
      setLoading("");
    }
  }

  const answerText = results.prediction?.prediction?.answer_text;
  const rawAnswerText = results.prediction?.prediction?.raw_answer_text;
  const deployment = results.prediction?.deployment;
  const prediction = results.prediction?.prediction;

  return (
    <div className="page-shell">
      <div className="app-frame">
        <header className="hero">
          <div className="hero-copy">
            <p className="eyebrow">Tuned Gemini Workspace</p>
            <h1>Ask Your Fine-Tuned Model</h1>
            <p className="lede">
              Paste the tuning job resource, ask a Python question, and read the
              tuned answer in a calm, focused workspace.
            </p>
          </div>
          <div className="hero-badge">
            <span>Resolved Endpoint</span>
            <strong>
              {deployment?.tuned_model_endpoint_name || "Will resolve after prediction"}
            </strong>
          </div>
        </header>

        <main className="workspace-grid">
          <section className="composer-card">
            <div className="section-heading">
              <p className="section-kicker">Input</p>
              <h2>Question Composer</h2>
            </div>

            <label>
              Tuning job resource
              <textarea
                rows="4"
                value={predictionForm.tuning_job_resource_name}
                onChange={(event) =>
                  setPredictionForm({
                    ...predictionForm,
                    tuning_job_resource_name: event.target.value,
                  })
                }
              />
            </label>

            <label>
              Your question
              <textarea
                rows="10"
                value={predictionForm.question}
                onChange={(event) =>
                  setPredictionForm({
                    ...predictionForm,
                    question: event.target.value,
                  })
                }
              />
            </label>

            <button
              className="primary-action"
              onClick={() =>
                runAction("generatePrediction", async () => {
                  const predictionResult = await generatePrediction(predictionForm);
                  setResults((prev) => ({ ...prev, prediction: predictionResult }));
                  return predictionResult;
                })
              }
            >
              {loading === "generatePrediction" ? "Generating..." : "Ask Model"}
            </button>

            <ResultSummary results={results} />
          </section>

          <section className="answer-panel">
            <div className="section-heading">
              <p className="section-kicker">Output</p>
              <h2>Model Answer</h2>
            </div>

            <div className="answer-meta">
              <div className="answer-stat">
                <span>Latency</span>
                <strong>
                  {prediction?.latency_seconds
                    ? `${prediction.latency_seconds}s`
                    : "--"}
                </strong>
              </div>
              <div className="answer-stat">
                <span>Finish reason</span>
                <strong>{prediction?.finish_reason || "--"}</strong>
              </div>
              <div className="answer-stat">
                <span>Blocked</span>
                <strong>{prediction ? String(prediction.blocked) : "--"}</strong>
              </div>
            </div>

            <div className="answer-card">
              <span>Response</span>
              {answerText ? (
                <div className="answer-text">{answerText}</div>
              ) : (
                <div className="answer-text muted-answer">
                  Your answer will appear here after you submit a question.
                </div>
              )}
            </div>

            {prediction?.usage_metadata &&
            Object.keys(prediction.usage_metadata).length ? (
              <div className="details-card">
                <span>Usage metadata</span>
                <pre>{JSON.stringify(prediction.usage_metadata, null, 2)}</pre>
              </div>
            ) : null}

            {rawAnswerText && rawAnswerText !== answerText ? (
              <details className="raw-output">
                <summary>Show raw model output</summary>
                <pre>{rawAnswerText}</pre>
              </details>
            ) : null}
          </section>
        </main>
      </div>
    </div>
  );
}

export default App;
