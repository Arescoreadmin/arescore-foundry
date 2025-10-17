#!/usr/bin/env bash
set -euo pipefail

# Inputs from workflow env
PR_NUMBER="${PR_NUMBER:-}"
REPO="${GITHUB_REPOSITORY:-}"
BASE_REF="${BASE_REF:-}"
HEAD_REF="${HEAD_REF:-}"

# Tools
yq() { docker run --rm -i -v "$PWD":"$PWD" -w "$PWD" mikefarah/yq:4 "$@"; }

# Read policy
MAX_LOC=$(yq '.codex.tasks.max_loc_per_task' codex.yml)
REVIEWERS_REQ=$(yq '.codex.git.reviewers_required' codex.yml)
BR_PREFIX=$(yq '.codex.git.branch_prefix' codex.yml)
REQ_LABELS=$(yq -r '.codex.git.pr_labels[]' codex.yml | xargs)
MAX_PARALLEL=$(yq '.codex.safe_defaults.max_parallel_prs' codex.yml)

echo "Policy: max_loc=$MAX_LOC reviewers=$REVIEWERS_REQ branch_prefix=$BR_PREFIX max_parallel_prs=$MAX_PARALLEL"
echo "Required labels: $REQ_LABELS"

# Count total changed LOC for this PR (adds + deletes)
# Prefer GitHub API to avoid weird rename heuristics
ADDS=$(gh api repos/$REPO/pulls/$PR_NUMBER -q .additions)
DELS=$(gh api repos/$REPO/pulls/$PR_NUMBER -q .deletions)
CHANGED=$(( ADDS + DELS ))
echo "PR #$PR_NUMBER LOC changed: +$ADDS/-$DELS = $CHANGED"
if (( CHANGED > MAX_LOC )); then
  echo "::error title=Guardrail: LOC cap exceeded::Changed LOC $CHANGED > cap $MAX_LOC"
  exit 1
fi

# Require labels
MISSING=()
for L in $REQ_LABELS; do
  if ! gh pr view "$PR_NUMBER" --json labels -q ".labels[].name" | grep -qx "$L"; then
    MISSING+=("$L")
  fi
done
if (( ${#MISSING[@]} > 0 )); then
  echo "::error title=Guardrail: missing labels::Missing: ${MISSING[*]}"
  exit 1
fi

# If labeled codex, enforce branch prefix
BRANCH=$(gh pr view "$PR_NUMBER" --json headRefName -q .headRefName)
if gh pr view "$PR_NUMBER" --json labels -q ".labels[].name" | grep -qx codex; then
  case "$BRANCH" in
    "$BR_PREFIX"*) : ;;
    *) echo "::error title=Guardrail: branch naming::Branch '$BRANCH' must start with '$BR_PREFIX'"
       exit 1 ;;
  esac
fi

# Approvals count
APPROVALS=$(gh pr view "$PR_NUMBER" --json reviews -q '[.reviews[] | select(.state=="APPROVED")] | length')
if (( APPROVALS < REVIEWERS_REQ )); then
  echo "::error title=Guardrail: approvals::Have $APPROVALS, need $REVIEWERS_REQ"
  exit 1
fi

# Max parallel codex PRs
OPEN_CODEX=$(gh pr list --state open --label codex --json number -q 'length')
if (( OPEN_CODEX > MAX_PARALLEL )); then
  echo "::error title=Guardrail: parallel PRs::Open codex PRs $OPEN_CODEX > cap $MAX_PARALLEL"
  exit 1
fi

echo "Codex guardrails: ok"
