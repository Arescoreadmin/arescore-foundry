#!/usr/bin/env bash
set -euo pipefail

# Where to write artifacts (override in CI with ARTIFACT_DIR)
ARTIFACT_DIR="${ARTIFACT_DIR:-artifacts}"
mkdir -p "$ARTIFACT_DIR/sbom" "$ARTIFACT_DIR/digests"

# List of compose services to report on (override via SERVICES)
SERVICES_DEFAULT=(orchestrator fl_coordinator consent_registry evidence_bundler spawn_service)
read -r -a SERVICES <<< "${SERVICES:-${SERVICES_DEFAULT[*]}}"

# Prefer docker sbom if present; otherwise run syft in a container
have_docker_sbom() { docker sbom --help >/dev/null 2>&1; }

sbom_for_image() {
  local img="$1" out="$2"
  if have_docker_sbom; then
    docker sbom --format spdx-json "$img" > "$out"
  else
    # no docker sbom; use syft via container
    docker run --rm -e SYFT_CHECK_FOR_APP_UPDATE=false \
      -v /var/run/docker.sock:/var/run/docker.sock \
      anchore/syft:latest "docker:$img" -o spdx-json > "$out"
  fi
}

digest_for_image() {
  local img="$1"
  # Prefer RepoDigests (immutable)
  docker inspect --format='{{index .RepoDigests 0}}' "$img" 2>/dev/null || true
}

echo "==> Collecting image names from compose"
# Works with single or multiple compose files (allow override via COMPOSE_FILES)
COMPOSE_FILES="${COMPOSE_FILES:-"-f compose.yml -f compose.federated.yml"}"
# shellcheck disable=SC2086
mapfile -t IMAGES < <(docker compose $COMPOSE_FILES config --images | sort -u)

echo "==> Generating SBOMs + digests"
: > "$ARTIFACT_DIR/digests/images.txt"
for img in "${IMAGES[@]}"; do
  # Only process images actually used by our SERVICES (best-effort filter)
  for svc in "${SERVICES[@]}"; do
    if [[ "$img" == *"$svc"* ]]; then
      sbom_out="$ARTIFACT_DIR/sbom/${svc}.spdx.json"
      echo "  - $svc -> $img"
      sbom_for_image "$img" "$sbom_out"
      dgst="$(digest_for_image "$img")"
      printf "%-20s %s\n" "$svc" "${dgst:-<no-digest-found>}" | tee -a "$ARTIFACT_DIR/digests/images.txt" >/dev/null
      break
    fi
  done
done

echo "==> Writing summary"
cat > "$ARTIFACT_DIR/digests/README.md" <<EOF
# AresCore Foundry — Image Digests

\`\`\`
$(cat "$ARTIFACT_DIR/digests/images.txt")
\`\`\`

Each SBOM is SPDX JSON under \`sbom/\` with file name matching the service name.
EOF

echo "OK: SBOMs and digests in $ARTIFACT_DIR/ (attach as CI artifacts)"
