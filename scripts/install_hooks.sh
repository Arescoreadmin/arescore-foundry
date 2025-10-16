#!/usr/bin/env bash
set -euo pipefail
# Reuse the repo's pre-commit if present
if [ -f .git/hooks/pre-commit ]; then
  chmod +x .git/hooks/pre-commit
  echo "pre-commit hook already present"
  exit 0
fi
# Minimal safety hook
cat > .git/hooks/pre-commit <<'HOOK'
#!/usr/bin/env bash
set -e
# Enforce Makefile tabs
if git diff --cached --name-only | grep -xq 'Makefile'; then
  if grep -n '^[[:space:]]\+[[:alnum:]$_({]' Makefile | grep -vq $'\t'; then
    echo "Makefile: recipe lines must start with a TAB." >&2
    exit 1
  fi
fi
# Block CRLF anywhere in staged diffs
if git diff --cached --binary | grep -q $'\r'; then
  echo "CRLF detected in staged changes. Convert to LF." >&2
  exit 1
fi
HOOK
chmod +x .git/hooks/pre-commit
echo "hooks installed"
