.PHONY: help clean docs
.DEFAULT_GOAL := help

define PRINT_HELP_PYSCRIPT
import re, sys

print("Available targets:\n")
for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

ifeq ($(OS),Windows_NT)
robot_args = --exclude skip --exclude posix
rm = -rmdir /s /q
else
robot_args = --exclude skip --exclude windows
rm = rm -fr
endif

bold := $(shell tput bold)
sgr0 := $(shell tput sgr0)
define title
@echo "\n$(bold)*** $(1) ***$(sgr0)\n"
endef

help: ## Print this help
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: ## Remove all build/test artifacts
	$(rm) dist/
	$(rm) docs/build/
	$(rm) docs/source/libdoc/
	$(rm) .pytest_cache
	$(rm) temp/
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.egg-info' -exec rm -rf {} +
	find . -name "__pycache__" -exec rm -rf {} +

install: ## Install development environment
	@poetry install

lint: ## Verify code formatting and conventions
	$(call title,"Verifying black")
	poetry run black --check src tests

	$(call title,"Verifying flake8")
	poetry run flake8 src

	$(call title,"Verifying pylint")
	poetry run pylint src/RPA

test: test-python test-robot ## Run all acceptance tests

test-python: ## Run python unittests
	poetry run pytest -v tests/python

test-robot: ## Run Robot Framework tests
	$(rm) tests/results
	poetry run robot\
	 $(robot_args)\
	 $(EXTRA_ROBOT_ARGS)\
	 --loglevel TRACE\
	 --pythonpath tests/resources\
	 --outputdir tests/results\
	 tests/robot

todo: ## Print all TODO/FIXME comments
	poetry run pylint --disable=all --enable=fixme --exit-zero src/

docs: docs-libdoc ## Generate documentation using Sphinx
	poetry run $(MAKE) -C docs clean
	poetry run $(MAKE) -C docs html

docs-libdoc: ## Prebuild libdoc files
	poetry run python\
	 ./tools/libdocext.py\
	 --rpa\
	 --title "Robot Framework API"\
	 --docstring rest\
	 --override-docstring src/RPA/Browser.py=robot\
	 --override-docstring src/RPA/HTTP.py=robot\
	 --format rest\
	 --override-format src/RPA/Browser.py=rest-html\
	 --override-format src/RPA/HTTP.py=rest-html\
	 --ignore src/RPA/core\
	 --output docs/source/libdoc/\
	 src/

docs-hub: docs-libdoc ## Generate documentation for Robohub
	mkdir -p dist/hub/markdown

	$(call title,"Building Markdown documentation")
	poetry run $(MAKE) -C docs clean
	poetry run $(MAKE) -C docs jekyll
	find docs/build/jekyll/libraries/ -name "index.md"\
	 -exec sh -c 'cp {} dist/hub/markdown/$$(basename $$(dirname {})).md' cp {} \;

	$(call title,"Building JSON documentation")
	poetry run python\
	 ./tools/libdocext.py\
	 --rpa\
	 --docstring rest\
	 --format json-html\
	 --override-docstring src/RPA/Browser.py=robot\
	 --override-docstring src/RPA/HTTP.py=robot\
	 --ignore src/RPA/core\
	 --output dist/hub/json\
	 --collapse\
	 src/

build: lint test ## Build distribution packages
	poetry build -vv

publish: build ## Publish package to PyPI
	poetry publish -v
