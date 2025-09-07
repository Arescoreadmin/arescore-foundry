// somewhere like src/main.js or wherever you call the API
import client from './api/client';

// optional: see what we're pointing at
console.log('API base:', client.API_BASE);

// quick smoke test – should log { status: "ok" } in the browser console
client.health()
  .then((h) => console.log('orchestrator health:', h))
  .catch((e) => console.error('health check failed:', e));

console.log('API_BASE =', API_BASE);

(async () => {
  try {
    const health = await apiGet('health'); // calls `${API_BASE}/health`
    console.log('orchestrator health:', health);
  } catch (e) {
    console.error(e);
  }
})();
