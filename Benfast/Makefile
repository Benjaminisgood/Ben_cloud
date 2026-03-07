PYTEST_DISABLE_PLUGIN_AUTOLOAD ?= 1
export PYTEST_DISABLE_PLUGIN_AUTOLOAD

VENV ?= venv
PYTHON ?= $(VENV)/bin/python
PIP ?= $(PYTHON) -m pip
PORT ?= 8700

.PHONY: ensure-venv install dev test check docs-build docs-serve

ensure-venv:
	@if [ ! -x "$(PYTHON)" ]; then \
		echo "[INFO] creating venv: $(VENV)"; \
		python3 -m venv "$(VENV)"; \
	fi

install: ensure-venv
	$(PIP) install -q --upgrade pip
	$(PIP) install -q -e ".[dev]"

dev: ensure-venv
	TESTING=false APP_ENV=development $(PYTHON) -m uvicorn src:app --reload --host 0.0.0.0 --port $(PORT)

test: ensure-venv
	TESTING=true APP_ENV=testing SWAGGER_UI_PASSWORD=test_password $(PYTHON) -m pytest -q

check: ensure-venv
	$(PYTHON) -m compileall -q src
	$(MAKE) test

docs-build:
	PYTHONPATH=src $(PYTHON) scripts/build_unified_site.py

docs-serve:
	$(PYTHON) -m http.server 8800 --directory $(abspath site)
