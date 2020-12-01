.PHONY: help clean install
.DEFAULT_GOAL := help

# Help script

define print_help
import re, sys

print("Available targets:\n")
for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export print_help

# Constants

configs = ../../config
docs = ../../docs
tools = ../../tools

exports = requirements.txt requirements-dev.txt setup.py

# Platform-specific variables

ifeq ($(OS),Windows_NT)
rm = -rmdir /s /q
mkdir = mkdir
sync = @cd .
robot_args = --exclude skip --exclude posix
else
rm = rm -fr
mkdir = mkdir -p
sync = @sync
robot_args = --exclude skip --exclude windows
endif

# Logging

bold := $(shell tput bold)
sgr0 := $(shell tput sgr0)
define title
@echo "\n$(bold)*** $(1) ***$(sgr0)\n"
endef

# Targets

help: ## Print this help
	@python -c "$${print_help}" < $(MAKEFILE_LIST)

clean: ## Remove all build/test artifacts
	$(rm) .pytest_cache
	$(rm) .venv
	$(rm) dist
	$(rm) tests/temp
	$(rm) $(exports)
	find . -name "__pycache__" -exec rm -rf {} +
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.egg-info' -exec rm -rf {} +

install: .venv/flag ## Install development environment

.venv/flag: poetry.lock
	@poetry config -n --local virtualenvs.in-project true
	$(sync)
	poetry install
	-touch $@

poetry.lock: pyproject.toml
	poetry lock

lint: install ## Verify code formatting and conventions
	$(call title,"Verifying black")
	poetry run black --check src/RPA tests/

	$(call title,"Verifying flake8")
	poetry run flake8 --config $(configs)/flake8 src/RPA

	$(call title,"Verifying pylint")
	poetry run pylint -j1 --rcfile $(configs)/pylint src/RPA

test: install ## Run all unittests
	poetry run pytest

todo: install ## Print all TODO/FIXME comments
	poetry run pylint --disable=all --enable=fixme --exit-zero src/

exports: install ## Create setup.py and requirements.txt files
	poetry export --without-hashes -f requirements.txt -o requirements.txt
	poetry export --dev --without-hashes -f requirements.txt -o requirements-dev.txt
	$(tools)/setup.py

build: lint test ## Build distribution packages
	# poetry build -vv
	# running these separately works around relative path problem
	# https://github.com/python-poetry/poetry/issues/266#issuecomment-636627858
	poetry build -vv -f sdist
	poetry build -vv -f wheel

publish: build ## Publish package to PyPI
	poetry publish -v
