PYTHON ?= python3
VENV ?= .venv
RUN = $(VENV)/bin/python

.PHONY: dev demo lint format format-check test build check

dev:
	$(PYTHON) -m venv $(VENV)
	$(RUN) -m pip install -e '.[dev]'

demo:
	$(RUN) -m skillvet examples/clean-skill --json

lint:
	$(RUN) -m ruff check skillvet tests scripts _build_backend.py

format:
	$(RUN) -m ruff format skillvet tests scripts _build_backend.py

format-check:
	$(RUN) -m ruff format --check skillvet tests scripts _build_backend.py

test:
	$(RUN) -m pytest --cov=skillvet --cov-report=term-missing --cov-fail-under=70

build:
	$(RUN) -m build

check: lint format-check test build
