// src/config.js
// Centralized runtime/build-time config + tiny API helpers.
// Runtime comes from /config.js (served by nginx, no-cache).
// Build-time comes from Vite env vars (e.g., VITE_API_BASE).

const RUNTIME =
  (typeof window !== 'undefined' && window.__APP_CONFIG__) || {};
const BUILD =
  (typeof import.meta !== 'undefined' && import.meta.env) || {};

export const API_BASE =
  (RUNTIME.API_BASE && String(RUNTIME.API_BASE)) ||
  (BUILD.VITE_API_BASE && String(BUILD.VITE_API_BASE)) ||
  '/api';

/** Join API_BASE with a path safely */
export function apiUrl(path = '') {
  const base = API_BASE.replace(/\/+$/, '');
  const p = String(path).replace(/^\/+/, '');
  return p ? `${base}/${p}` : base;
}

/** Simple GET helper that returns JSON when possible */
export async function apiGet(path, opts = {}) {
  const res = await fetch(apiUrl(path), {
    method: 'GET',
    headers: { Accept: 'application/json', ...(opts.headers || {}) },
    ...opts,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    const err = new Error(
      `GET ${apiUrl(path)} -> ${res.status} ${res.statusText}${text ? `: ${text}` : ''}`
    );
    err.status = res.status;
    throw err;
  }

  const ct = res.headers.get('content-type') || '';
  return ct.includes('application/json') ? res.json() : res.text();
}

/** Convenience: URL for orchestrator health */
export const healthUrl = () => apiUrl('health');
