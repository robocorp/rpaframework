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
mkdir = mkdir
sync = @cd .
else
rm = rm -fr
mkdir = mkdir -p
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
	$(rm) docs/source/robot/
	$(rm) docs/source/prebuild/
	find . -name "__pycache__" -exec rm -rf {} +

clean-each: ./packages/*
	$(call make_each, "clean")

install: .venv/flag ## Install development environment

.venv/flag: poetry.lock
	@poetry config -n --local virtualenvs.in-project true
	$(sync)
	poetry install
	-touch $@

poetry.lock: pyproject.toml
	poetry lock

docs: docs-each docs-libdoc install ## Generate documentation using Sphinx
	poetry run $(MAKE) -C docs clean
	poetry run $(MAKE) -C docs html
	poetry run python ./tools/merge.py docs/source/json/ docs/build/html/latest.json

docs-each: packages/*
	$(call make_each, "docs-sphinx")

docs-hub: docs-hub-each ## Generate distributable documentation for Robohub
	$(call title,"Building Markdown documentation")
	poetry run $(MAKE) -C docs clean
	poetry run $(MAKE) -C docs markdown
	$(mkdir) dist/hub/markdown/
	poetry run python ./tools/hub.py \
		docs/source/libraries/ \
		docs/build/markdown/libraries/ \
		dist/hub/markdown/

docs-hub-each: packages/*
	$(call make_each, "docs-hub")

docs-libdoc: install ## Generate documentation using Robot Framework Libdoc
	poetry run docgen --format html --output docs/source/libdoc/ RPA.*
	# TODO: Remove these when non-importables are _private
	$(rm) docs/source/libdoc/RPA_core*
	$(rm) docs/source/libdoc/RPA_recognition*
	$(rm) docs/source/libdoc/RPA_Desktop_keywords*
	$(rm) docs/source/libdoc/RPA_Desktop_utils*
	poetry run docgen --format json-html --output docs/source/json/ RPA.*
	# TODO: Remove these when non-importables are _private
	$(rm) docs/source/json/RPA_core*
	$(rm) docs/source/json/RPA_recognition*
	$(rm) docs/source/json/RPA_Desktop_keywords*
	$(rm) docs/source/json/RPA_Desktop_utils*

changelog: ## Print changes in latest release
	poetry run python ./tools/changelog.py

build-each: packages/*
	$(call make_each, "build")
