# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RPA Framework is a collection of open-source Python libraries for Robotic Process Automation (RPA), designed for both Robot Framework and Python. This is a **monorepo** containing 12 interdependent packages managed by `uv` (with legacy Poetry support).

**Documentation:** https://rpaframework.org/

## Monorepo Structure

```
packages/
├── core/       # Core utilities: webdriver, geometry, decorators, Windows helpers
├── main/       # Primary RPA Framework: Excel, SAP, Salesforce, Browser, etc.
├── windows/    # Windows UI automation (UIAutomation, PyWinAuto)
├── assistant/  # RPA Assistant UI functionality
├── pdf/        # PDF processing
├── recognition/# Image recognition and OCR (support package)
├── aws/        # AWS cloud integration
├── google/     # Google APIs integration
├── hubspot/    # HubSpot CRM integration
├── openai/     # OpenAI API integration
├── sema4ai/    # Sema4 AI platform integration
└── devutils/   # Shared development utilities
```

Each package has: `src/RPA/`, `tests/python/`, `tests/robot/`, `pyproject.toml`, `tasks.py`, `.venv/`

## Common Commands

All commands use the `invoke` task runner. Run from package directory unless noted.

### Setup
```bash
# Initial setup (from repo root)
pip install invoke
python -m pip install -Ur invocations/requirements.txt
invoke install-invocations

# Install package dependencies
invoke install

# Install with extras
invoke install --extra playwright --extra aws
```

### Testing
```bash
# Run all tests (Python + Robot)
invoke code.test

# Python tests only
invoke code.test-python

# Single Python test file
uv run pytest tests/python/test_filename.py -vv -s

# Specific test function
uv run pytest tests/python/test_file.py::TestClass::test_method -vv -s

# Robot Framework tests
invoke code.test-robot

# Specific robot test
invoke code.test-robot -r filename -t "Test Name"
```

### Linting & Formatting
```bash
invoke code.lint              # Run pylint
invoke code.lint -e           # Exit on failure (used in CI)
invoke code.format-code       # Format code
invoke code.type-check        # Run MyPy
```

### Building & Publishing
```bash
invoke build                  # Build package
invoke build.publish --ci     # Publish to DevPI (testing)
invoke build.publish          # Publish to PyPI (production)
```

### Documentation (from repo root)
```bash
invoke docs.build             # Build Sphinx docs
invoke docs.host              # Host locally at localhost:8000
```

### Useful Commands
```bash
invoke --list                 # List all available tasks
invoke code.test --help       # Help for specific task
invoke install.local          # Install local package for cross-package dev
invoke install --reset        # Reset to clean state
```

## Architecture Notes

### Library Design Pattern
- Each library is a Python class with methods exposed as Robot Framework keywords
- Public methods (no `_` prefix) become Robot Framework keywords automatically
- Use `@keyword` decorator for RF-specific customization
- All public methods require type annotations and docstrings with both Python and RF examples

### Package Dependencies
- `core` is a dependency of most packages (changes here affect everything)
- `main` includes most libraries; heavy dependencies split into separate packages
- `recognition` and `core` are support packages (no standalone libraries)

### Testing Structure
- `tests/python/` - pytest unit tests
- `tests/robot/` - Robot Framework integration tests
- `tests/resources/` - shared test data
- Tags `skip` and `manual` exclude tests from default runs

## CI/CD

GitHub Actions workflows in `.github/workflows/` - one per package. Tests run on:
- Windows, Ubuntu, macOS
- Python 3.9, 3.10, 3.11
- Environment variable `INVOKE_IS_CI_CD=1` indicates CI context

## Development Workflow

1. Create feature branch: `feature/name`, `hotfix/issue`, `release/version`
2. Make changes, write tests
3. Run `invoke code.lint -e` and `invoke code.test`
4. Update `docs/source/releasenotes.rst` with changes
5. Create PR to master
6. After merge: bump version in `pyproject.toml`, `invoke build.publish`
