# scripts/prompt_one_file.sh
#!/usr/bin/env bash
set -euo pipefail
PATH_TARGET="${1:?target path required, e.g. frontend/nginx.conf}"
SPEC_PATH="${2:-docs/codex/frontend-nginx-spec.md}"

SPEC_B64="$(base64 -w 0 "$SPEC_PATH")"

mkdir -p sessions
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="sessions/${STAMP}_one-file_prompt.txt"

cat > "$OUT" <<'PROMPT'
You are generating a single file. Return ONLY the file content.
Do not add commentary. Do not add diff markers.

# Path
{{PATH}}

# Spec (base64, UTF-8). Decode and follow strictly.
{{SPEC_B64}}

# Output format
Return fenced code with the correct language if applicable.
No preface, no epilogue, no extra text.
PROMPT

# Inject vars safely
sed -i \
  -e "s|{{PATH}}|$PATH_TARGET|g" \
  -e "s|{{SPEC_B64}}|$SPEC_B64|g" \
  "$OUT"

echo "Prompt written to $OUT"
echo "Paste that into your model and
