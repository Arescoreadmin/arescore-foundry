import { API_BASE, health } from './api/client.js';

console.log('API base:', API_BASE);

async function boot() {
  const root = document.getElementById('root');
  root.innerHTML = `
    <main style="font-family:system-ui,Segoe UI,Arial;margin:2rem">
      <h1>Sentinel Forge</h1>
      <p id="status">Pinging <code>${API_BASE}/ready</code>…</p>
      <pre id="out" style="background:#111;color:#0f0;padding:1rem;border-radius:8px;overflow:auto"></pre>
    </main>
  `;

  try {
    const res = await health();
    document.getElementById('status').textContent = 'OK';
    document.getElementById('out').textContent = JSON.stringify(res, null, 2);
  } catch (e) {
    document.getElementById('status').textContent = 'FAILED';
    document.getElementById('out').textContent = String(e);
  }
}

boot();
