#!/usr/bin/env python3
import os, sys, time, json, subprocess, shlex, textwrap

def run_list(args, cwd=None, check=True, capture=False):
    print("==> $", " ".join(shlex.quote(a) for a in args))
    if capture:
        res = subprocess.run(args, cwd=cwd, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             check=check)
        return res.stdout
    subprocess.run(args, cwd=cwd, check=check)

def repo_root():
    here = os.getcwd()
    rel = os.path.join("infra", "docker-compose.yml")
    cur = here
    while True:
        if os.path.isfile(os.path.join(cur, rel)):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            print("Could not find infra/docker-compose.yml from", here)
            sys.exit(1)
        cur = parent

def docker_health(name):
    out = run_list(["docker","inspect","--format","{{json .State.Health.Status}}",name],
                   capture=True).strip()
    try:
        return json.loads(out)
    except Exception:
        return out or "unknown"

def docker_health_logs(name, limit=8):
    fmt = "{{range .State.Health.Log}}{{.End}}  code={{.ExitCode}}  {{.Output}}{{println}}{{end}}"
    out = run_list(["docker","inspect","--format",fmt,name], capture=True)
    lines = [ln for ln in out.splitlines() if ln.strip()]
    print("\nRecent health checks:")
    print("\n".join(lines[-limit:]))

def wait_healthy(name, timeout=180):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        status = docker_health(name)
        if status != last:
            print("health:", status)
            last = status
        if status == "healthy":
            return True
        time.sleep(2)
    return False

def main():
    root = repo_root()
    print("Repo root:", root)

    base = os.path.join(root, "infra", "docker-compose.yml")
    override = os.path.join(root, "infra", "compose.healthcheck.override.yml")

    # VALID YAML: use a block scalar for the python -c program as the last list item.
    override_body = textwrap.dedent("""\
    services:
      frostgatecore:
        healthcheck:
          test:
            - CMD
            - python
            - -c
            - |
              import json,sys,urllib.request as u
              try:
                  r=u.urlopen('http://localhost:8001/health', timeout=2)
                  sys.exit(0 if json.loads(r.read() or b'{}').get('ok') else 1)
              except Exception:
                  sys.exit(1)
          interval: 10s
          timeout: 3s
          retries: 5
          start_period: 10s
    """)

    os.makedirs(os.path.dirname(override), exist_ok=True)
    with open(override, "w", encoding="utf-8") as f:
        f.write(override_body)
    print("Wrote override:", override)

    run_list([
        "docker","compose",
        "-f", base,
        "-f", override,
        "up","-d","--build","--force-recreate","--no-deps","frostgatecore"
    ], cwd=root)

    if not wait_healthy("frostgatecore", timeout=120):
        docker_health_logs("frostgatecore")
        print("\nStill not healthy. Check app logs:\n  docker logs frostgatecore --since=3m")
        sys.exit(1)

    docker_health_logs("frostgatecore")

    # In-container probe without heredoc
    probe_code = (
        "import json,sys,urllib.request as u; "
        "r=u.urlopen('http://localhost:8001/health',timeout=2); "
        "print('status:', r.status, 'body:', r.read())"
    )
    run_list(["docker","exec","-i","frostgatecore","python","-c",probe_code])

    # Try to nudge RAG caches; tolerate missing requests/curl.
    try:
        import uuid, requests
        cid = str(uuid.uuid4())
        headers = {"X-Correlation-ID": cid}
        requests.post("http://localhost:8001/dev/embed",
                      json={"text":"The   quick   brown    fox"},
                      headers=headers, timeout=3)
        requests.get("http://localhost:8001/dev/q",
                     params={"q":"ping pong","k":"5"},
                     headers=headers, timeout=3)
        requests.get("http://localhost:8001/dev/q",
                     params={"q":"ping pong","k":"5"},
                     headers=headers, timeout=3)
    except Exception:
        try:
            cid = run_list(["python","-c","import uuid; print(uuid.uuid4())"], capture=True).strip()
            run_list(["curl","-s","-H",f"X-Correlation-ID: {cid}",
                      "-H","content-type: application/json",
                      "-d","{\"text\":\"The   quick   brown    fox\"}",
                      "http://localhost:8001/dev/embed"])
            run_list(["curl","-s","-H",f"X-Correlation-ID: {cid}",
                      "http://localhost:8001/dev/q?q=ping%20pong&k=5"])
            run_list(["curl","-s","-H",f"X-Correlation-ID: {cid}",
                      "http://localhost:8001/dev/q?q=ping%20pong&k=5"])
        except Exception:
            pass

    # Show last RAGCACHE hits if present
    try:
        out = run_list(["docker","logs","frostgatecore","--since=2m"], capture=True)
        lines = [ln for ln in out.splitlines() if "RAGCACHE " in ln]
        if lines:
            print("\nRAGCACHE recent:\n" + "\n".join(lines[-10:]))
    except Exception:
        pass

    print("\nDone.")

if __name__ == "__main__":
    sys.exit(main() or 0)
