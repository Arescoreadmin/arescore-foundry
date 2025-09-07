# YAML configuration should be in a separate .yml file, not in this Python script.

# Python script starts here

APP = {
    "orchestrator":  {"context": "./orchestrator",  "port": 8080},   # adjust if needed
    "observer_hub":  {"context": "./observer_hub",  "port": 9092},
    "metrics_tuner": {"context": "./metrics_tuner", "port": 9102},
}

def update_service_healthcheck(svc, port):
    env = svc.get("environment") or {}
    if env.get("HEALTH_PORT") != port:
        env["HEALTH_PORT"] = port
        svc["environment"] = env
        changed = True
    else:
        changed = False

    hp = "$${HEALTH_PORT}"  # escape for docker-compose, expand in container
    hc = {
        "test": [
            "CMD-SHELL",
            f"wget -qO- http://localhost:{hp}/health >/dev/null 2>&1 || "
            f"curl -fsS http://localhost:{hp}/health >/dev/null 2>&1 || exit 1",
        ],
        "interval": "10s",
        "timeout": "2s",
        "retries": 12,
        "start_period": "15s",
    }
    if svc.get("healthcheck") != hc:
        svc["healthcheck"] = hc
        changed = True

    return changed
