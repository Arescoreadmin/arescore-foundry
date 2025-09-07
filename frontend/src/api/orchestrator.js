export async function runScript(path){
  const res = await fetch('/api/orchestrator/run-script', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({path})});
  return res.json();
}
export async function cloneEnv(){
  const res = await fetch('/api/orchestrator/clone', {method:'POST'});
  return res.json();
}