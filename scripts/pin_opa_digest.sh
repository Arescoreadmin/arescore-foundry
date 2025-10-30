# scripts/pin_opa_digest.sh
#!/usr/bin/env bash
set -euo pipefail

COMPOSE_MAIN="${COMPOSE_MAIN:-infra/docker-compose.yml}"
COMPOSE_OPA="${COMPOSE_OPA:-infra/compose.opa.yml}"
SERVICE_NAME="${SERVICE_NAME:-opa}"
RESTART_OPA="${RESTART_OPA:-1}"

die(){ echo "ERROR: $*" >&2; exit 1; }
need(){ command -v "$1" >/dev/null || die "missing tool: $1"; }

need docker
need python3
[[ -f "$COMPOSE_MAIN" ]] || die "Missing $COMPOSE_MAIN"
[[ -f "$COMPOSE_OPA"  ]] || die "Missing $COMPOSE_OPA"

echo ">> Resolving current image from effective compose (JSON)…"
json="$(docker compose -f "$COMPOSE_MAIN" -f "$COMPOSE_OPA" config --format json 2>/dev/null \
  || die "compose config failed; fix YAML first")"

effective_image="$(
  python3 - "$SERVICE_NAME" <<'PY'
import sys,json
svc=sys.argv[1]
cfg=json.load(sys.stdin)
try:
    print(cfg["services"][svc]["image"])
except KeyError:
    # try to reconstruct from service name if no image set
    # fall back to official OPA tag we know we use
    print("openpolicyagent/opa:0.67.0")
PY
)" || die "failed to parse effective image"

# strip existing digest if any
repo_tag="${effective_image%@*}"
if ':' in repo_tag:
    repo, tag = repo_tag.rsplit(':',1)
else:
    repo, tag = repo_tag, 'latest'

# pull + resolve digest
echo ">> docker pull ${repo}:${tag}"
docker pull "${repo}:${tag}" >/dev/null
repo_digest="$(docker inspect --format '{{join .RepoDigests "\n"}}' "${repo}:${tag}" \
  | grep -E "^${repo}@sha256:[a-f0-9]{64}$" || true)"
if [[ -z "$repo_digest" ]]; then
  repo_digest="$(docker inspect --format '{{index .RepoDigests 0}}' "${repo}:${tag}")"
fi
[[ -n "$repo_digest" ]] || die "Could not resolve digest for ${repo}:${tag}"
digest="${repo_digest#*@}"
[[ "$digest" =~ ^sha256:[a-f0-9]{64}$ ]] || die "Bad digest: $digest"

pinned="${repo}:${tag}@${digest}"
echo ">> Resolved digest: $pinned"

# backup
bak="$COMPOSE_OPA.bak.$(date +%s)"
cp -v "$COMPOSE_OPA" "$bak" >/dev/null || true

# insert or replace image: under the service block without awk ‘in’
tmp="$(mktemp)"
python3 - "$SERVICE_NAME" "$pinned" "$COMPOSE_OPA" > "$tmp" <<'PY'
import sys, re, io
svc, newimg, path = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(path,'r',encoding='utf-8').read()

# Find '  svc:' line
pat_header = re.compile(rf'(^[ ]{{2}}{re.escape(svc)}:[^\n]*\n)', re.M)
m = pat_header.search(text)
if not m:
    # no service block here; append a minimal one
    block = f"  {svc}:\n    image: {newimg}\n"
    if "services:" in text:
        text = re.sub(r'services:\s*\n', lambda mm: mm.group(0)+block, text, count=1, flags=re.M)
    else:
        text = "services:\n" + block + text
else:
    start = m.end()
    # Determine end of block: next line that starts with two spaces then a non-space, and not the same header
    # Simpler: split the file into lines and iterate
    lines = text.splitlines(True)
    hdr_idx = text[:start].count('\n')  # line index AFTER header
    # Walk forward until next "  <something>:" at col 0 (two spaces)
    end_idx = len(lines)
    for i in range(hdr_idx, len(lines)):
        if re.match(r'^[ ]{2}\S.*:\s*$', lines[i]) and not lines[i].startswith(f"  {svc}:"):
            end_idx = i
            break
    block = ''.join(lines[hdr_idx:end_idx])

    # Replace image: if present; else insert after command:/volumes:/ports: if any, otherwise first line
    if re.search(r'^[ ]{4}image:\s*.+$', block, re.M):
        block = re.sub(r'^[ ]{4}image:\s*.+$', f"    image: {newimg}", block, count=1, flags=re.M)
    else:
        # insert after command: if exists, else after volumes/ports/healthcheck/read_only, else at top
        keys = ['command:', 'volumes:', 'ports:', 'healthcheck:', 'read_only:', 'cap_drop:', 'security_opt:', 'restart:']
        insert_pos = 0
        last_match = -1
        for i,l in enumerate(block.splitlines(True)):
            if any(l.lstrip().startswith(k) for k in keys):
                last_match = i
        blines = block.splitlines(True)
        if last_match >= 0:
            blines.insert(last_match+1, f"    image: {newimg}\n")
        else:
            blines.insert(0, f"    image: {newimg}\n")
        block = ''.join(blines)

    # Reassemble
    text = text[:start] + block + ''.join(lines[end_idx:])

sys.stdout.write(text)
PY
mv "$tmp" "$COMPOSE_OPA"

echo ">> Validating compose…"
docker compose -f "$COMPOSE_MAIN" -f "$COMPOSE_OPA" config >/dev/null
echo "✅ compose valid with pinned image"

if [[ "$RESTART_OPA" == "1" ]]; then
  echo ">> Recreating OPA…"
  docker compose -f "$COMPOSE_MAIN" -f "$COMPOSE_OPA" up -d --force-recreate "$SERVICE_NAME"
  for i in {1..60}; do
    if curl -fsS http://127.0.0.1:8181/health >/dev/null 2>&1; then
      echo "✅ OPA healthy (pinned)"
      exit 0
    fi
    sleep 1
  done
  echo "⚠️  OPA not healthy yet; logs tail:"
  docker compose -f "$COMPOSE_MAIN" -f "$COMPOSE_OPA" logs --no-log-prefix "$SERVICE_NAME" | tail -200
  exit 1
else
  echo ">> Skipping restart (RESTART_OPA=0)."
fi
