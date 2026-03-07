#!/usr/bin/env python3
"""Standalone EdgeDriver integration test for issue #1312.

Verifies that:
  1. EdgeDriver binary can be downloaded (tests azureedge.net -> microsoft.com
     redirect fix from PR #1227) — this is the primary test
  2. A headless Edge session can be started (end-to-end, requires Edge browser installed)

Expected to FAIL with selenium==4.15.2 exact pin (old azureedge.net CDN issues).
Expected to PASS after fix: selenium>=4.15.2,<5.0.0 (newer version resolved).

Exit codes:
    0 — download succeeded (session also started if Edge browser is installed)
    1 — download or session failed unexpectedly

Usage:
    python test_edge_driver.py
    # or from packages/core directory:
    uv run python tests/python/test_edge_driver.py
"""
import shutil
import sys
from pathlib import Path


def main() -> int:
    import importlib.metadata

    selenium_ver = importlib.metadata.version("selenium")
    print(f"Selenium version: {selenium_ver}")

    # Step 1: download EdgeDriver — exercises the azureedge.net redirect patch
    try:
        from RPA.core import webdriver

        results_dir = Path(__file__).parent / "results"
        results_dir.mkdir(exist_ok=True)
        print("Downloading EdgeDriver...")
        driver_path = webdriver.download("Edge", root=results_dir)
        print(f"  Driver downloaded: {driver_path}")
    except Exception as exc:
        print(f"\nFAIL (download): {type(exc).__name__}: {exc}")
        return 1

    # Step 2: start a headless Edge session — requires Edge browser to be installed
    edge_binary = shutil.which("msedge") or shutil.which("microsoft-edge")
    if not edge_binary:
        # Also check the standard macOS application path
        macos_edge = Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge")
        if macos_edge.exists():
            edge_binary = str(macos_edge)

    if not edge_binary:
        print(
            "\nPASS (download only): EdgeDriver downloaded successfully. "
            "Edge browser not installed — skipping session test."
        )
        return 0

    try:
        from selenium import webdriver as selenium_webdriver
        from selenium.webdriver import EdgeOptions
        from selenium.webdriver.edge.service import Service

        options = EdgeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.binary_location = edge_binary
        service = Service(driver_path)
        print(f"Starting headless Edge session (binary: {edge_binary})...")
        driver = selenium_webdriver.Edge(service=service, options=options)
        try:
            driver.get("about:blank")
            title = driver.title
        finally:
            driver.quit()
        print(f"  Session OK, page title: '{title}'")
    except Exception as exc:
        print(f"\nFAIL (session): {type(exc).__name__}: {exc}")
        return 1

    print("\nPASS: EdgeDriver download and session both work correctly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
