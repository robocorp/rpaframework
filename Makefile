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
copy = copy
else
rm = rm -fr
mkdir = mkdir -p
sync = @sync
copy = cp
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
	poetry run rfbrowser init --skip-browsers

poetry.lock: pyproject.toml
	poetry lock

docs: docs-libdoc install ## Generate documentation using Sphinx
	poetry run $(MAKE) -C docs clean
	poetry run python ./tools/todos.py packages/main/src docs/source/contributing/todos.rst
	poetry run python ./tools/merge.py docs/source/json/ docs/source/include/latest.json
	poetry run $(MAKE) -C docs html
	poetry run python ./tools/rss.py

docs-libdoc: install ## Generate documentation using Robot Framework Libdoc
	poetry run docgen\
		--template docs/source/template/libdoc/libdoc.html\
		--format html\
		--output docs/source/include/libdoc/\
		--exclude RPA.core*\
		--exclude RPA.recognition*\
		--exclude RPA.scripts*\
		--exclude RPA.Desktop.keywords*\
		--exclude RPA.Desktop.utils*\
		--exclude RPA.PDF.keywords*\
		--exclude RPA.Cloud.objects*\
		--exclude RPA.Cloud.Google.keywords*\
		--exclude RPA.Robocorp.utils*\
		--exclude RPA.Dialogs.*\
		rpaframework

	poetry run python -c "import shutil; shutil.copy2('docs/source/template/iframeResizer.contentWindow.map', 'docs/source/include/libdoc/')"

	poetry run docgen\
		--no-patches\
		--format json-html\
		--output docs/source/json/\
		--exclude RPA.core*\
		--exclude RPA.recognition*\
		--exclude RPA.scripts*\
		--exclude RPA.Desktop.keywords*\
		--exclude RPA.Desktop.utils*\
		--exclude RPA.PDF.keywords*\
		--exclude RPA.Cloud.objects*\
		--exclude RPA.Cloud.Google.keywords*\
		--exclude RPA.Robocorp.utils*\
		--exclude RPA.Dialogs.*\
		rpaframework

changelog: ## Print changes in latest release
	poetry run python ./tools/changelog.py

build-each: packages/*
	$(call make_each, "build")

lint-each: packages/*
	$(call make_each, "lint")

install-hooks: ## Install git hooks
	git config core.hooksPath ./config/git-hooks/

local: ## Serve docs from local http server
	poetry run python -m http.server -d docs/build/html/
