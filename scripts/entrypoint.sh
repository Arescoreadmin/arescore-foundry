# 1) Patch the orchestrator Dockerfile to ensure the entrypoint is executable
applypatch() {
  awk '
    BEGIN{done=0}
    {print}
    /COPY services\/orchestrator\/entrypoint.sh \/entrypoint.sh/ && done==0 {
      print "RUN chmod +x /entrypoint.sh"
      done=1
    }' services/orchestrator/Dockerfile > /tmp/orch.Dockerfile && \
  mv /tmp/orch.Dockerfile services/orchestrator/Dockerfile
}
applypatch
unset -f applypatch

# 2) Rebuild & restart orchestrator only
docker compose build orchestrator --no-cache
docker compose up -d orchestrator

# 3) Probe from inside its netns (most reliable)
ORCH_CID="$(docker compose ps -q orchestrator)"; test -n "$ORCH_CID"
docker run --rm --network "container:${ORCH_CID}" curlimages/curl:8.10.1 -fsS http://127.0.0.1:8080/health && echo "orchestrator: OK"

# 4) (Optional) host-level check should now pass too
curl -fsS http://127.0.0.1:8080/health && echo "host OK"
