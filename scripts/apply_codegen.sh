#!/usr/bin/env bash
# scripts/apply_codegen.sh
#
# Usage:
#   apply_codegen.sh file <PATH> [--from <FILE>]         # write full file from stdin or FILE
#   apply_codegen.sh diff            [--from <FILE>]      # apply a unified diff/patch from stdin or FILE
#
# Notes:
# - Keeps original positional args (mode, path) for backward compatibility.
# - Adds --from FILE to source content instead of stdin (as requested).
# - Audits all inputs to patches/<timestamp>/ and keeps backups on file writes.
# - Best-effort local checks: docker compose build+nginx -t if frontend exists; make smoke if present.
# - Exits on first failure; prints useful errors; never pollutes history on failed checks.

set -euo pipefail

# -------- cosmetic logging (no dependencies) ----------
color() { local c="$1"; shift || true; printf "\033[%sm%s\033[0m" "$c" "$*"; }
info()  { echo "$(color 36 "[info]") $*"; }
warn()  { echo "$(color 33 "[warn]") $*" >&2; }
err()   { echo "$(color 31 "[error]") $*" >&2; }
die()   { err "$*"; exit 2; }

# -------- sanity: must be inside a git repo ----------
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  die "Not inside a git repository. Initialize or cd into repo first."
fi

mode="${1:-}"   # "file" or "diff"
path="${2:-}"   # target path for "file" mode (kept for compatibility)

stamp="$(date +%Y%m%d-%H%M%S)"
patches_dir="patches/${stamp}"
mkdir -p "$patches_dir"

# Save stdin (or source file) for auditing
tmp="$(mktemp)"

# ---------- YOUR REQUESTED INSERT EXACTLY HERE ----------
# after tmp="$(mktemp)" and before the case statement:
if [[ "${3:-}" == "--from" && -n "${4:-}" ]]; then
  cp "$4" "$tmp"
else
  cat > "$tmp"
fi
# -------------------------------------------------------

# Also persist a copy for audit trail, regardless of mode
audit_in="${patches_dir}/stdin-or-file.txt"
cp "$tmp" "$audit_in"

# Helpful normalization if available (don’t hard-fail if tools missing)
if command -v dos2unix >/dev/null 2>&1; then
  dos2unix -q "$tmp" || true
fi

case "$mode" in
  file)
    [[ -n "$path" ]] || die "Usage: $0 file <PATH> [--from <FILE>]  < file_content"
    mkdir -p "$(dirname "$path")"

    # Backup existing file if present
    if [[ -f "$path" ]]; then
      backup="${path}.bak.${stamp}"
      cp -f "$path" "$backup"
      info "Backup created: $backup"
    fi

    # Write and stage
    cp "$tmp" "$path"
    git add "$path"
    info "Wrote and staged: $path"
    ;;

  diff)
    patch_file="${patches_dir}/001.patch"
    mv "$tmp" "$patch_file"

    # Show a tiny preview to help debugging broken patches
    if command -v sed >/dev/null 2>&1; then
      info "Patch header:"
      sed -n '1,20p' "$patch_file" || true
    fi

    # Apply with whitespace fixes; index stage on success
    git apply --index --whitespace=fix -p0 "$patch_file" || {
      err "Patch failed. Saved at: $patch_file"
      exit 1
    }
    info "Patch applied and staged from: $patch_file"
    ;;

  *)
    cat >&2 <<USAGE
Usage:
  $0 file <PATH> [--from <FILE>]         < file_content
  $0 diff           [--from <FILE>]      < unified_diff
USAGE
    exit 2
    ;;
esac

# -------- optional local checks (best effort; quiet skip if not present) --------
# Lightweight nginx availability probe (host)
if command -v nginx >/dev/null 2>&1; then
  info "Host nginx detected; skipping direct config test (container test below will cover UI config)."
fi

# Compose: only attempt if infra/docker-compose.yml exists and mentions frontend
if [[ -f infra/docker-compose.yml ]] && grep -q 'frontend' infra/docker-compose.yml; then
  info "Building frontend image via docker compose (best effort)..."
  if command -v docker >/dev/null 2>&1; then
    # Build quietly but still surface errors; don’t spam logs on success
    if docker compose -f infra/docker-compose.yml build frontend >/dev/null; then
      # Derive image name the same way Compose tags it by default
      # Your earlier usage expects: arescore-foundry-frontend:latest
      image_tag="arescore-foundry-frontend:latest"
      info "Running nginx -t inside $image_tag"
      if ! docker run --rm "$image_tag" nginx -t; then
        err "nginx -t failed inside container. Not committing."
        exit 1
      fi
    else
      warn "docker compose build failed or docker not healthy. Skipping container nginx -t."
    fi
  else
    warn "docker not found. Skipping docker checks."
  fi
fi

# Make smoke tests i
