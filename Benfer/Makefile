.PHONY: install test check

PYTEST_DISABLE_PLUGIN_AUTOLOAD ?= 1
PYTHON ?= $(shell if [ -x venv/bin/python ] && PYTEST_DISABLE_PLUGIN_AUTOLOAD=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD) venv/bin/python -m pytest --version >/dev/null 2>&1; then echo venv/bin/python; elif [ -x /Users/ben/miniforge3/bin/python ] && PYTEST_DISABLE_PLUGIN_AUTOLOAD=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD) /Users/ben/miniforge3/bin/python -m pytest --version >/dev/null 2>&1; then echo /Users/ben/miniforge3/bin/python; else echo python3; fi)

install:
	./benfer.sh install

test:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD) PYTHONPATH=apps/api/src $(PYTHON) -m pytest -q tests

check:
	PYTHONPATH=apps/api/src $(PYTHON) -m compileall -q apps/api/src/benfer_api
	$(MAKE) test PYTHON="$(PYTHON)" PYTEST_DISABLE_PLUGIN_AUTOLOAD="$(PYTEST_DISABLE_PLUGIN_AUTOLOAD)"
