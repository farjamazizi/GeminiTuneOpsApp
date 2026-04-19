import os
import shutil
import subprocess

import google.auth

DEFAULT_PROJECT_ID = "project-2bb7b579-5b60-4790-8c2"


def _get_gcloud_project():
    """Best-effort lookup of the active gcloud project."""
    gcloud = shutil.which("gcloud.cmd") or shutil.which("gcloud")
    if not gcloud:
        return None

    try:
        result = subprocess.run(
            [gcloud, "config", "get-value", "project"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return None

    project_id = result.stdout.strip()
    if project_id and project_id != "(unset)":
        return project_id

    return None


def authenticate():
    """Return application default credentials and the active GCP project ID."""
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", DEFAULT_PROJECT_ID)

    credentials, project_id = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )

    project_id = (
        project_id
        or os.getenv("GOOGLE_CLOUD_PROJECT")
        or os.getenv("GCLOUD_PROJECT")
        or _get_gcloud_project()
    )
    if not project_id:
        raise RuntimeError(
            "Could not determine your Google Cloud project ID. "
            "Set GOOGLE_CLOUD_PROJECT or configure `gcloud config set project YOUR_PROJECT_ID`."
        )

    return credentials, project_id
