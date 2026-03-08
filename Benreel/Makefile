.PHONY: install dev test check migrate-smoke ci db-upgrade db-revision db-current layout-guard

PYTEST_DISABLE_PLUGIN_AUTOLOAD ?= 1

layout-guard:
	test ! -d app
	test ! -d frontend
	test ! -d test
	test ! -f database.db
	test ! -f requirements.txt

install:
	cd apps/api && python3 -m pip install -e ".[dev]"

dev:
	cd apps/api && PYTHONPATH=src alembic upgrade head
	cd apps/api && PYTHONPATH=src uvicorn benreel_api.main:app --app-dir src --reload --host 0.0.0.0 --port 9500

test:
	cd apps/api && PYTEST_DISABLE_PLUGIN_AUTOLOAD=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD) PYTHONPATH=src pytest -q

check:
	$(MAKE) layout-guard
	cd apps/api && PYTHONPATH=src python -m compileall -q src/benreel_api
	cd apps/api && PYTEST_DISABLE_PLUGIN_AUTOLOAD=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD) PYTHONPATH=src pytest -q
	cd apps/api && PYTHONPATH=src alembic current

migrate-smoke:
	cd apps/api && DATABASE_URL=sqlite:////tmp/Benreel_migrate_smoke.sqlite PYTHONPATH=src alembic upgrade head
	rm -f /tmp/Benreel_migrate_smoke.sqlite

ci: check migrate-smoke

db-upgrade:
	cd apps/api && PYTHONPATH=src alembic upgrade head

db-revision:
	cd apps/api && PYTHONPATH=src alembic revision --autogenerate -m "$(m)"

db-current:
	cd apps/api && PYTHONPATH=src alembic current
