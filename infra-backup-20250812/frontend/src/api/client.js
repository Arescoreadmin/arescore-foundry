/**
 * Reads API base from window at runtime, falls back to '/api'.
 * IMPORTANT: Prefer setting window.API_BASE in public/config.js.
 */
export const API_BASE =
  (typeof window !== 'undefined' && (window.API_BASE || (window.__APP_CONFIG__ && window.__APP_CONFIG__.API_BASE)))
  || '/api';

export async function apiGet(path, opts = {}) {
  const resp = await fetch(`${API_BASE}${path}`, { ...opts });
  if (!resp.ok) throw new Error(`GET ${path} -> ${resp.status}`);
  return resp.json();
}

// match orchestrator route we added
export const health = () => apiGet('/ready');

export default { API_BASE, apiGet, health };
