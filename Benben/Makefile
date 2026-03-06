PYTEST_DISABLE_PLUGIN_AUTOLOAD ?= 1
PYTHON ?= $(shell if PYTEST_DISABLE_PLUGIN_AUTOLOAD=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD) python3 -m pytest --version >/dev/null 2>&1; then echo python3; elif [ -x /Users/ben/miniforge3/bin/python ]; then echo /Users/ben/miniforge3/bin/python; else echo python3; fi)

.PHONY: test check
test:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD) PYTHONPATH=. $(PYTHON) -m pytest -q

check:
	$(PYTHON) -m compileall -q .
	$(MAKE) test PYTHON="$(PYTHON)"
