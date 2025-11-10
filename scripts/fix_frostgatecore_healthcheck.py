#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import textwrap
import time

def run(cmd, cwd=None, check=True, capture=False):
    print("==> $", cmd)
    if capture:
        res = subprocess.run(cmd, cwd=cwd, shell=True, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             check=check)
        return res.stdout
    subprocess.run(cmd, cwd=cwd, shell=True, check=check)

def find_repo_root():
    here = os.getcwd()
    candidate = here
    rel = os.path.join("infra", "docker-compose.yml")
    while True:
        if os.path.isfile(os.path.join(candidate, rel)):
            return candidate
        parent = os.path.dirname(candidate)
        if parent == candidate:
            print("Could not find infra/docker-compose.yml from", here)
            sys.exit(1)
        candidate = parent

def get_health(name):
    fmt = '{{json .State.Health.Status}}'
    try:
        out = run(f'docker inspect --format "{fmt}" {name}', capture=True).strip()
        return json.loads(out)
    except subprocess.CalledProcessError as e:
        if e.stdout:
            print(e.stdout)
        return "unknown"
    except Exception:
        return "unknown"

def main():
    repo = find_repo_root()
    print("Repo root:", repo)

    base_compose = os.path.join(repo, "infra", "docker-compose.yml")
    override_path = os.path.join(repo, "infra", "compose.healthcheck.override.yml")

    override = textwrap.dedent("""\
    services:
      frostgatecore:
        healthcheck:
          test: ["CMD", "python", "-c", "import json,sys,urllib.request; u='http://localhost:8001/health';\\ntry:\\n r=urllib.request.urlopen(u,timeout=2); d=json.loads(r.read() or b'{}'); sys.exit(0 if d.get('ok') else 1)\\nexcept Exception:\\n sys.exit(1)"]
          interval: 10s
          timeout: 3s
          retries: 5
          start_period: 10s
    """)
    os.makedirs(os.path.dirname(override_path), exist_ok=True)
    with open(override_path, "w", encoding="utf-8") as f:
        f.write(override)
    print("Wrote override:", override_path)

    up_cmd = f'docker compose -f "{base_compose}" -f "{override_path}" up -d --build --force-recreate --no-deps frostgatecore'
    run(up_cmd, cwd=repo)

    name = "frostgatecore"
    deadline = time.time() + 180
    last = None
    while time.time() < deadline:
        status = get_health(name)
        if status != last:
            print("health:", status)
            last = status
        if status == "healthy":
            break
        time.sleep(2)

    # Show last few health logs
    try:
        logs_fmt = "{{range .State.Health.Log}}{{.End}}  code={{.ExitCode}}  {{.Output}}{{println}}{{end}}"
        out = run(f'docker inspect --format "{logs_fmt}" {name}', capture=True)
        print("\nRecent health checks:\n" + out)
    except subprocess.CalledProcessError:
        pass

    # Robust probe inside the container using a here-doc (works on Git Bash, WSL, etc.)
    probe = r"""docker exec -i {name} sh -lc 'python - <<\"PY\"
import json, sys, urllib.request
try:
    with urllib.request.urlopen("http://localhost:8001/health", timeout=2) as r:
        print("status:", r.status, "body:", r.read())
except Exception as e:
    print("healthcheck failed:", repr(e)); sys.exit(1)
PY
'""".format(name=name)
    run(probe)

    print("\nDone.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted. Check status with:\n  docker inspect --format \"{{.State.Health.Status}}\" frostgatecore")
        sys.exit(130)
    except subprocess.CalledProcessError as e:
        print("\nCommand failed:")
        print(e.stdout or "")
        sys.exit(e.returncode)
