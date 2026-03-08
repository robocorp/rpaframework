#!/usr/bin/env bash
# Pre-push hook for packages/main — runs lint, fast tests, and AI review locally.
# Install: cp packages/main/scripts/pre-push.sh .git/hooks/pre-push && chmod +x .git/hooks/pre-push
# Skip AI review: AI_REVIEW=0 git push

set -e
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT/packages/main"

echo ">>> Running pylint..."
uv run pylint --rcfile ../../config/pylint src

echo ">>> Running fast tests (no browser required)..."
uv run pytest tests/python/test_browser.py \
    -k "not (TestSelenium or TestRelativeLocators or TestBrowserLogs or TestNetworkInterception or TestVirtualAuthenticator)" \
    -v

# AI review (advisory — never blocks the push; set AI_REVIEW=0 to skip)
if [[ "${AI_REVIEW:-1}" != "0" ]]; then
    bash "$REPO_ROOT/packages/main/scripts/ai-review.sh"
fi

echo ">>> OK — pushing."
