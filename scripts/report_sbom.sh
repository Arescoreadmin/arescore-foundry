#!/usr/bin/env bash
set -euo pipefail

PROJECT_NAME="${PROJECT_NAME:-arescore-foundry}"
COMPOSE_FILES="${COMPOSE_FILES:--f compose.yml -f compose.federated.yml}"
ARTIFACT_DIR="${ARTIFACT_DIR:-artifacts}"

mkdir -p "$ARTIFACT_DIR"

log()  { printf '==> %s\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }
c() { docker compose -p "$PROJECT_NAME" $COMPOSE_FILES "$@"; }

have_docker_sbom() { docker sbom --help >/dev/null 2>&1; }
have_syft()        { command -v syft >/dev/null 2>&1; }

# --- image discovery (unchanged) ---
log "Collecting image names from compose (project: $PROJECT_NAME)"
SERVICES=() IMAGES=() LINES=()

if OUT="$(c images --format json 2>/dev/null || true)"; then
  if [ -n "${OUT:-}" ]; then
    mapfile -t LINES < <(python3 - <<'PY' <<<"$OUT" 2>/dev/null || true
import json,sys
try:
  for row in json.load(sys.stdin):
    svc = row.get("Service") or row.get("Name") or ""
    img = row.get("Image") or ""
    if svc and img: print(f"{svc}\t{img}")
except Exception: pass
PY
)
  fi
fi

if [ ${#LINES[@]} -eq 0 ]; then
  if OUT="$(c ps --format json 2>/dev/null || true)"; then
    if [ -n "${OUT:-}" ]; then
      mapfile -t LINES < <(python3 - <<'PY' <<<"$OUT" 2>/dev/null || true
import json,sys
try:
  for row in json.load(sys.stdin):
    svc=row.get("Service") or ""; img=row.get("Image") or ""
    if svc and img: print(f"{svc}\t{img}")
except Exception: pass
PY
)
    fi
  fi
fi

if [ ${#LINES[@]} -eq 0 ]; then
  if OUT="$(c ps --format '{{.Service}}\t{{.Image}}' 2>/dev/null || true)"; then
    [ -n "${OUT:-}" ] && mapfile -t LINES < <(printf '%s\n' "$OUT" | awk 'NF>=2')
  fi
fi

if [ ${#LINES[@]} -eq 0 ]; then
  if OUT="$(c ps 2>/dev/null || true)"; then
    hdr="$(printf '%s\n' "$OUT" | head -n1)"
    svc_col=$(awk -v h="$hdr" 'BEGIN{split(h,f);for(i=1;i<=length(f);i++)if(f[i]=="SERVICE"){print i;exit}}')
    img_col=$(awk -v h="$hdr" 'BEGIN{split(h,f);for(i=1;i<=length(f);i++)if(f[i]=="IMAGE"){print i;exit}}')
    if [ -n "${svc_col:-}" ] && [ -n "${img_col:-}" ]; then
      mapfile -t LINES < <(printf '%s\n' "$OUT" \
        | tail -n +2 \
        | awk -v s="$svc_col" -v m="$img_col" '
            NF>=m {svc=$s; img=$m; for(i=m+1;i<=NF;i++) img=img" "$i; print svc "\t" img}
          ')
    fi
  fi
fi

if [ ${#LINES[@]} -eq 0 ]; then
  warn "No images discovered. Ensure the stack is up and project name matches."
  warn "Try: docker compose -p ${PROJECT_NAME} $COMPOSE_FILES up -d"
  exit 0
fi

for line in "${LINES[@]}"; do
  svc="${line%%$'\t'*}"
  img="${line#*$'\t'}"
  [ -n "$svc" ] && [ -n "$img" ] || continue
  SERVICES+=("$svc"); IMAGES+=("$img")
done

DIGEST_REPORT="$ARTIFACT_DIR/digests.txt"
SBOM_INDEX="$ARTIFACT_DIR/SBOM_INDEX.md"
: > "$DIGEST_REPORT"; : > "$SBOM_INDEX"

{
  echo "# Release Artifacts"; echo
  echo "## Image Digests"; echo '```'
} >> "$SBOM_INDEX"

log "Generating SBOMs + digests"
for i in "${!IMAGES[@]}"; do
  svc="${SERVICES[$i]}"; img="${IMAGES[$i]}"
  printf "  - %-18s -> %s\n" "$svc" "$img"

  digest="$(docker image inspect "$img" --format '{{index .RepoDigests 0}}' 2>/dev/null || true)"
  [ -z "$digest" ] && digest="$(docker image inspect "$img" --format '{{.Id}}' 2>/dev/null || true)"
  [ -z "$digest" ] && digest="UNKNOWN-DIGEST"
  printf "%-22s %s\n" "$svc" "$digest" | tee -a "$DIGEST_REPORT" >> "$SBOM_INDEX"

  sbom_path="$ARTIFACT_DIR/sbom-${svc}.spdx.json"

  # Try docker sbom
  if have_docker_sbom && docker sbom "$img" -o "spdx-json=$sbom_path" >/dev/null 2>&1; then
    continue
  fi

  # Try host syft
  if have_syft && syft "$img" -o spdx-json > "$sbom_path" 2>/dev/null; then
    continue
  fi

  # Final fallback: containerized syft
  if docker run --rm -u "$(id -u):$(id -g)" \
       -v /var/run/docker.sock:/var/run/docker.sock \
       -v "$(pwd)/$ARTIFACT_DIR:/out" \
       ghcr.io/anchore/syft:latest \
       "$img" -o spdx-json --file "/out/$(basename "$sbom_path")" >/dev/null 2>&1; then
    continue
  fi

  warn "SBOM generation failed for $img (docker sbom & syft)."
done

{
  echo '```'; echo; echo "## SBOM files"
  for i in "${!IMAGES[@]}"; do
    svc="${SERVICES[$i]}"; p="$ARTIFACT_DIR/sbom-${svc}.spdx.json"
    [ -f "$p" ] && echo "- $(basename "$p")"
  done
} >> "$SBOM_INDEX"

log "Wrote digests to: $DIGEST_REPORT"
log "Wrote SBOM index to: $SBOM_INDEX"
