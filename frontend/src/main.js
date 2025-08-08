// --- BEGIN: runtime client smoke test ---
import client from './api/client';

(async () => {
  try {
    const res = await client.get('/health'); // calls http://localhost:8000/health via /api
    console.log('API health:', res);          // expect: { status: "ok" }
  } catch (err) {
    console.error('API health failed:', err);
  }
})();
// --- END: runtime client smoke test ---
const apiBase = import.meta.env.VITE_API_BASE || "http://localhost:8000";
const el = document.getElementById("app");
el.innerHTML = `
  <main style="font-family: system-ui, sans-serif; padding: 2rem;">
    <h1>Sentinel Foundry</h1>
    <p>Frontend is running.</p>
    <p>API base: <code>${apiBase}</code></p>
    <ul>
      <li><a href="${apiBase}/health" target="_blank">Orchestrator /health</a></li>
      <li><a href="http://localhost:3000/health" target="_blank">Frontend /health (nginx)</a></li>
    </ul>
  </main>
`;
