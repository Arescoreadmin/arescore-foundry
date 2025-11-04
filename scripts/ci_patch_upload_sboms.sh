#!/usr/bin/env bash
set -euo pipefail

WF="${WF:-.github/workflows/staging-release.yml}"
MARK_BEGIN="# BEGIN: SBOM UPLOAD STEPS (auto-injected)"
MARK_END="# END: SBOM UPLOAD STEPS (auto-injected)"

if [[ ! -f "$WF" ]]; then
  echo "ERROR: $WF not found (run from repo root)." >&2
  exit 1
fi

# Idempotency guard
if grep -qF "$MARK_BEGIN" "$WF"; then
  echo "Already present: SBOM upload steps in $WF"
  exit 0
fi

bak="$WF.bak.$(date +%s)"
cp "$WF" "$bak"
echo "Backed up to $bak"

tmp="$(mktemp)"

awk -v MARK_BEGIN="$MARK_BEGIN" -v MARK_END="$MARK_END" '
  function spaces(n,    s){s=""; for(i=0;i<n;i++) s=s " "; return s}
  function indent_of(s,   m){ m=match(s,/^[ ]*/); return RLENGTH }

  # Print the upload steps with list indentation = li
  function print_block(li,    si){
    si = spaces(li)
    print si MARK_BEGIN
    print si "- name: Upload digests"
    print si "  uses: actions/upload-artifact@v4"
    print si "  with:"
    print si "    name: digests"
    print si "    path: artifacts/digests.txt"
    print ""
    print si "- name: Upload SBOMs"
    print si "  uses: actions/upload-artifact@v4"
    print si "  with:"
    print si "    name: sboms"
    print si "    path: artifacts/sbom-*.spdx.json"
    print ""
    print si "- name: Upload SBOM index"
    print si "  uses: actions/upload-artifact@v4"
    print si "  with:"
    print si "    name: sbom-index"
    print si "    path: artifacts/SBOM_INDEX.md"
    print si MARK_END
  }

  BEGIN{
    in_steps=0
    steps_indent=-1  # indent of the "steps:" key
    item_indent=-1   # indent of current "- " list item
    want_after_item=0
    pending_li=-1
    inserted=0
    release_matched=0
    saw_first_steps=0
  }

  {
    line=$0
    print_now=1

    # Enter a steps: block
    if ($0 ~ /^[ ]*steps:[ ]*$/) {
      in_steps=1
      steps_indent = indent_of($0)
      saw_first_steps=1
    } else if (in_steps) {
      # Leaving steps: when indent goes back to or above steps key (and non-blank)
      if (indent_of($0) <= steps_indent && $0 !~ /^[ ]*$/) {
        if (want_after_item && !inserted) {
          print_block(pending_li)
          inserted=1
          want_after_item=0
        }
        in_steps=0
      }
    }

    # Track list item starts within steps:
    if (in_steps && $0 ~ /^[ ]*-[ ]+/) {
      if (want_after_item && !inserted) {
        print_block(pending_li)
        inserted=1
        want_after_item=0
      }
      item_indent = indent_of($0)
    }

    # Detect the release run line
    if (in_steps && $0 ~ /^[ ]*run:[ ]*/) {
      l = $0
      gsub(/["'\''"]/, "", l)                  # strip quotes
      if (l ~ /prod_release_final\.sh/ || l ~ /(^|[[:space:]])make[[:space:]]+release([[:space:]]|$)/) {
        release_matched=1
        want_after_item=1
        pending_li=item_indent
      }
    }

    # Print current line
    if (print_now) print line
  }

  END{
    # If we matched the release step and never got a chance to inject (it was the last item),
    # inject now at the same list indentation.
    if (!inserted && want_after_item && pending_li>=0) {
      print_block(pending_li)
      inserted=1
    }

    # Fallback: if we saw a steps: block but never matched release, append at end of the first steps:
    if (!inserted && saw_first_steps) {
      # Use a common list indent of steps_indent+2
      li = steps_indent + 2
      if (li < 2) li = 2
      print_block(li)
      inserted=1
    }
  }
' "$WF" > "$tmp"

mv "$tmp" "$WF"
echo "Patched: $WF"
echo "Next: git add $WF && git commit -m 'ci: upload SBOMs & digests (staging)' && git push"
