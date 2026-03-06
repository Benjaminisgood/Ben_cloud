.PHONY: install test check migrate-smoke

PYTEST_DISABLE_PLUGIN_AUTOLOAD ?= 1
PYTHON ?= $(shell if [ -x .venv/bin/python ] && PYTEST_DISABLE_PLUGIN_AUTOLOAD=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD) .venv/bin/python -m pytest --version >/dev/null 2>&1; then echo .venv/bin/python; elif [ -x /Users/ben/miniforge3/bin/python ] && PYTEST_DISABLE_PLUGIN_AUTOLOAD=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD) /Users/ben/miniforge3/bin/python -m pytest --version >/dev/null 2>&1; then echo /Users/ben/miniforge3/bin/python; else echo python3; fi)

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD) PYTHONPATH=. $(PYTHON) -m pytest -q apps/tests

check:
	PYTHONPATH=. $(PYTHON) -m compileall -q apps
	$(MAKE) test PYTHON="$(PYTHON)" PYTEST_DISABLE_PLUGIN_AUTOLOAD="$(PYTEST_DISABLE_PLUGIN_AUTOLOAD)"

migrate-smoke:
	DATABASE_URL=sqlite:////tmp/bensci_migrate_smoke.sqlite PYTHONPATH=. $(PYTHON) -m alembic upgrade head
	rm -f /tmp/bensci_migrate_smoke.sqlite
