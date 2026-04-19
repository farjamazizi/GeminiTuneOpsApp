# CI/CD Roadmap

## Objective

Move `GeminiTuneOpsApp` from a notebook-derived local project into a repeatable delivery pipeline for:

- a Flask API that handles dataset preparation, tuning orchestration, tuning-status checks, and prediction serving
- a React frontend that presents a simple tuned-model Q&A workspace
- supporting scripts and deployment infrastructure around Vertex AI workflows

## Phase 1: Source Control and Standards

1. Place `GeminiTuneOpsApp` under Git with branch protection for `main`.
2. Add `.gitignore`, `.editorconfig`, and environment-specific config templates.
3. Introduce formatting and linting gates:
   - Backend: `ruff`, `black`, `pytest`
   - Frontend: `eslint`, `vitest`
4. Add pull request templates requiring risk notes for model, data, and prompt changes.

## Phase 2: Build and Test Automation

1. Create a backend pipeline that:
   - sets up Python
   - installs `requirements.txt` or `requirements-dev.txt` depending on the job
   - runs linting
   - runs unit and integration tests
2. Create a frontend pipeline that:
   - installs Node dependencies
   - runs linting and tests
   - builds the production bundle
3. Add a contract test layer for the Flask API with mocked Vertex AI and GCS clients.
4. Add smoke tests for the main app flow:
   - resolve a tuning resource
   - submit a prediction request
   - validate the answer payload shape

## Phase 3: Containerization

1. Add a backend Dockerfile for Flask with a production WSGI server such as `gunicorn`.
2. Add a frontend Dockerfile or produce a static build served by Nginx or Cloud Storage + CDN.
3. Publish images to Artifact Registry on every tagged release.

## Phase 4: Deployment Environments

1. Define `dev`, `staging`, and `prod` environments.
2. Use infrastructure as code for:
   - Cloud Run or GKE for Flask
   - Secret Manager for credentials and runtime config
   - Artifact Registry for images
   - Cloud Build or GitHub Actions runners
3. Promote the same artifact through environments rather than rebuilding per environment.

## Phase 5: Secure Delivery

1. Replace local credential files with Workload Identity or service-account bindings.
2. Store environment values in Secret Manager and inject them at deploy time.
3. Add dependency and container scanning:
   - `pip-audit`
   - `npm audit`
   - container vulnerability scans
4. Add approval gates before production deploys that affect prompts, safety handling, normalized output behavior, or model targets.

## Phase 6: Observability and Rollback

1. Centralize Flask logs and frontend telemetry in Cloud Logging.
2. Track key metrics:
   - tuning job success rate
   - dataset preparation success rate
   - prediction latency
   - normalized answer delivery success rate
   - safety blocks by category
   - citation counts and finish reasons
3. Add deployment health checks and automatic rollback triggers.
4. Preserve prior frontend bundles and backend image tags for fast rollback.

## Suggested pipeline stages

1. `validate`: lint, type checks, dependency audit
2. `test`: backend tests, frontend tests, API contract tests
3. `build`: backend image, frontend bundle
4. `scan`: image and dependency scanning
5. `deploy-dev`: automatic on merge to `main`
6. `deploy-staging`: automatic on release candidate tag
7. `deploy-prod`: manual approval with smoke tests and rollback plan

## Example GitHub Actions layout

- `.github/workflows/backend-ci.yml`
- `.github/workflows/frontend-ci.yml`
- `.github/workflows/e2e-smoke.yml`
- `.github/workflows/deploy-dev.yml`
- `.github/workflows/deploy-prod.yml`

## Near-term next steps

1. Add automated tests around each backend service module, especially prediction normalization and Google API error handling.
2. Add Dockerfiles and runtime configuration management.
3. Choose a deploy target such as Cloud Run for the Flask API.
4. Add frontend build validation and smoke tests around the tuned-resource question workspace.
5. Wire CI to build the React app and publish the backend as a container.
