.PHONY: install test check db-upgrade db-revision db-current migrate-smoke ci

PYTEST_DISABLE_PLUGIN_AUTOLOAD ?= 1
PYTHON ?= $(shell if [ -x venv/bin/python ] && PYTEST_DISABLE_PLUGIN_AUTOLOAD=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD) venv/bin/python -m pytest --version >/dev/null 2>&1; then echo venv/bin/python; elif [ -x /Users/ben/miniforge3/bin/python ] && PYTEST_DISABLE_PLUGIN_AUTOLOAD=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD) /Users/ben/miniforge3/bin/python -m pytest --version >/dev/null 2>&1; then echo /Users/ben/miniforge3/bin/python; else echo python3; fi)
ALEMBIC_PYTHON ?= $(shell if [ -x venv/bin/python ] && venv/bin/python -m alembic --help >/dev/null 2>&1; then echo "$$(pwd)/venv/bin/python"; elif [ -x /Users/ben/miniforge3/bin/python ] && /Users/ben/miniforge3/bin/python -m alembic --help >/dev/null 2>&1; then echo /Users/ben/miniforge3/bin/python; else command -v python3; fi)

install:
	./benfer.sh install

test:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD) PYTHONPATH=apps/api/src $(PYTHON) -m pytest -q tests

check:
	PYTHONPATH=apps/api/src $(PYTHON) -m compileall -q apps/api/src/benfer_api
	$(MAKE) test PYTHON="$(PYTHON)" PYTEST_DISABLE_PLUGIN_AUTOLOAD="$(PYTEST_DISABLE_PLUGIN_AUTOLOAD)"
	cd apps/api && PYTHONPATH=src $(ALEMBIC_PYTHON) -m alembic -c alembic.ini current

db-upgrade:
	cd apps/api && PYTHONPATH=src $(ALEMBIC_PYTHON) -m alembic -c alembic.ini upgrade head

db-revision:
	cd apps/api && PYTHONPATH=src $(ALEMBIC_PYTHON) -m alembic -c alembic.ini revision --autogenerate -m "$(m)"

db-current:
	cd apps/api && PYTHONPATH=src $(ALEMBIC_PYTHON) -m alembic -c alembic.ini current

migrate-smoke:
	cd apps/api && DATABASE_URL=sqlite:////tmp/benfer_migrate_smoke.sqlite PYTHONPATH=src $(ALEMBIC_PYTHON) -m alembic -c alembic.ini upgrade head
	rm -f /tmp/benfer_migrate_smoke.sqlite

ci: check migrate-smoke
