#!/usr/bin/env bash
# Pre-push hook for packages/main — runs lint and fast (non-browser) tests locally.
# Install: cp packages/main/scripts/pre-push.sh .git/hooks/pre-push && chmod +x .git/hooks/pre-push

set -e
cd "$(git rev-parse --show-toplevel)/packages/main"

echo ">>> Running pylint..."
uv run pylint --rcfile ../../config/pylint src

echo ">>> Running fast tests (no browser required)..."
uv run pytest tests/python/test_browser.py \
    -k "not (TestSelenium or TestRelativeLocators or TestBrowserLogs or TestNetworkInterception or TestVirtualAuthenticator)" \
    -v

echo ">>> OK — pushing."
