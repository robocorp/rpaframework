.PHONY: help clean docs
.DEFAULT_GOAL := help

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

ifeq ($(OS),Windows_NT)
rm = -rmdir /s /q
sync = @cd .
else
rm = rm -fr
sync = @sync
endif

define make_each
@for package in $^ ; do $(MAKE) -C "$${package}" $(1) || exit 1 ; done
endef

help: ## Print this help
	@python -c "$${print_help}" < $(MAKEFILE_LIST)

clean: clean-each ## Remove all build/test artifacts
	$(rm) .venv
	$(rm) docs/build/
	$(rm) docs/source/libdoc/
	$(rm) docs/source/prebuild/
	find . -name "__pycache__" -exec rm -rf {} +

clean-each: ./packages/*
	$(call make_each, "clean")

install: .venv/flag ## Install development environment

.venv/flag: poetry.lock
	@poetry config -n --local virtualenvs.in-project true
	$(sync)
	poetry install
	@touch $@

poetry.lock: pyproject.toml
	poetry lock

check: install ## Check that versions are up-to-date
	poetry run python ./tools/versions.py

docs: check docs-each ## Generate documentation using Sphinx
	poetry run $(MAKE) -C docs clean
	poetry run $(MAKE) -C docs html

docs-each: packages/*
	$(call make_each, "docs-libdoc")

changelog: ## Print changes in latest release
	poetry run python ./tools/changelog.py
