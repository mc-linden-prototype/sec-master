// Thin client for the versioned API. The API address comes from /config.js, written by the UI server.

const BASE = `${window.CASM_API || ''}/api/v1`;

export async function api(path, params = {}) {
  const url = new URL(`${BASE}${path}`, window.location.origin);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, value);
  });
  const response = await fetch(url);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = Array.isArray(body.detail) ? body.detail.map((d) => d.msg).join('; ') : body.detail;
    throw new Error(`${response.status} ${detail || response.statusText}`);
  }
  return response.json();
}

export async function health() {
  const response = await fetch(`${window.CASM_API || ''}/api/health`);
  return response.json();
}
