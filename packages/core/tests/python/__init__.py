from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent.parent
RESOURCES_DIR = TESTS_DIR / "resources"
RESULTS_DIR = TESTS_DIR / "results"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
