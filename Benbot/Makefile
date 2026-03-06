.PHONY: install dev test check migrate-smoke ci db-upgrade db-revision db-current layout-check

PYTEST_DISABLE_PLUGIN_AUTOLOAD ?= 1

install:
	cd apps/api && python3 -m pip install -e ".[dev]"

dev:
	cd apps/api && PYTHONPATH=src alembic upgrade head
	python app.py

test:
	cd apps/api && PYTEST_DISABLE_PLUGIN_AUTOLOAD=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD) PYTHONPATH=src pytest -q

layout-check:
	test ! -d test
	test -z "$$(find . -maxdepth 1 -name 'test_*.py' -print -quit)"

check:
	$(MAKE) layout-check
	cd apps/api && PYTHONPATH=src python -m compileall -q src/benbot_api
	cd apps/api && PYTEST_DISABLE_PLUGIN_AUTOLOAD=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD) PYTHONPATH=src pytest -q
	cd apps/api && PYTHONPATH=src alembic current

migrate-smoke:
	cd apps/api && DATABASE_URL=sqlite:////tmp/benbot_migrate_smoke.sqlite PYTHONPATH=src alembic upgrade head
	rm -f /tmp/benbot_migrate_smoke.sqlite

ci: check migrate-smoke

db-upgrade:
	cd apps/api && PYTHONPATH=src alembic upgrade head

db-revision:
	cd apps/api && PYTHONPATH=src alembic revision --autogenerate -m "$(m)"

db-current:
	cd apps/api && PYTHONPATH=src alembic current
