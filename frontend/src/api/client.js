/**
 * Minimal runtime API client.
 * Reads API base from window.__APP_CONFIG__ (served by /config.js),
 * falls back to '/api' when building or if the file isn't present.
 */
const conf = (typeof window !== 'undefined' && window.__APP_CONFIG__) ? window.__APP_CONFIG__ : {};
export const API_BASE = conf.API_BASE || '/api';

export async function apiGet(path, opts = {}) {
  const resp = await fetch(`${API_BASE}${path}`, { ...opts });
  if (!resp.ok) throw new Error(`GET ${path} -> ${resp.status}`);
  return resp.json();
}

// handy helper the app can call
export const health = () => apiGet('/health');

export default { API_BASE, apiGet, health };
