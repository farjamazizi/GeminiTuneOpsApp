const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }

  return response.json();
}

export function prepareData(payload) {
  return request("/data/prepare", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createTuningJob(payload) {
  return request("/tuning/jobs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getTuningStatus(resourceName, region) {
  const params = new URLSearchParams({ resource_name: resourceName, region });
  return request(`/tuning/jobs/status?${params.toString()}`);
}

export function generatePrediction(payload) {
  return request("/predictions/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function monitorPredictions(payload) {
  return request("/predictions/monitor", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
