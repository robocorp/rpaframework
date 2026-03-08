#!/usr/bin/env bash
# AI code review — runs Claude against the current branch diff (vs master).
#
# Usage:
#   ./packages/main/scripts/ai-review.sh          # review all changes vs master
#   ./packages/main/scripts/ai-review.sh --staged  # review only staged changes
#
# Called automatically by pre-push.sh; can also be run standalone.
# Requires `claude` (Claude Code CLI) to be on PATH.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
BASE_BRANCH="${AI_REVIEW_BASE:-master}"
STAGED_ONLY="${1:-}"

if ! command -v claude &>/dev/null; then
    echo ">>> ai-review: 'claude' not found on PATH — skipping AI review."
    exit 0
fi

# Build the diff
if [[ "$STAGED_ONLY" == "--staged" ]]; then
    DIFF="$(git -C "$REPO_ROOT" diff --cached)"
    DIFF_LABEL="staged changes"
else
    DIFF="$(git -C "$REPO_ROOT" diff "$BASE_BRANCH"...HEAD)"
    DIFF_LABEL="changes vs $BASE_BRANCH"
fi

if [[ -z "$DIFF" ]]; then
    echo ">>> ai-review: no diff found ($DIFF_LABEL) — skipping."
    exit 0
fi

DIFF_LINES="$(echo "$DIFF" | wc -l | tr -d ' ')"
echo ">>> Running AI review on $DIFF_LABEL ($DIFF_LINES lines of diff)..."

PROMPT="You are a senior Python code reviewer. Review the following git diff carefully.

Focus ONLY on real problems (not style nits). Flag:
- Wrong exception types raised (e.g. built-in TimeoutError instead of selenium TimeoutException)
- Missing guards for platform/driver-specific APIs (e.g. Chromium-only features called on Firefox)
- Misleading or incorrect error messages
- Import errors or removed APIs used
- Security issues (command injection, SQL injection, XSS, path traversal, etc.)
- Logic bugs that would cause test failures or silent misbehaviour
- CI/CD configuration mistakes (wrong working-directory, missing permissions, etc.)

Format your response as a concise bulleted list. If there are no issues, say 'No issues found.'
Group by severity: [HIGH], [MEDIUM], [LOW].

GIT DIFF:
$DIFF"

# Unset CLAUDECODE so this can run inside a Claude Code session (e.g. during /review)
echo "$PROMPT" | env -u CLAUDECODE claude --print --output-format text
EXIT_CODE=$?

echo ""
if [[ $EXIT_CODE -ne 0 ]]; then
    echo ">>> ai-review: claude exited with code $EXIT_CODE."
fi
exit 0  # AI review is advisory — never block the push
