.PHONY: install dev test check migrate-smoke ci db-upgrade db-revision db-current

PYTEST_DISABLE_PLUGIN_AUTOLOAD ?= 1

# Install the FastAPI backend
install:
	cd apps/api && python3 -m pip install -e ".[dev]"

# Start the FastAPI dev server
dev:
	cd apps/api && PYTHONPATH=src uvicorn benome_api.main:app --app-dir src --reload --host 0.0.0.0 --port 8200

# Run backend tests
test:
	cd apps/api && PYTEST_DISABLE_PLUGIN_AUTOLOAD=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD) PYTHONPATH=src pytest -q

# Run unified backend quality gate
check:
	cd apps/api && PYTHONPATH=src python -m compileall -q src/benome_api
	cd apps/api && PYTEST_DISABLE_PLUGIN_AUTOLOAD=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD) PYTHONPATH=src pytest -q
	cd apps/api && PYTHONPATH=src alembic current

# Run migration smoke test on temporary SQLite DB
migrate-smoke:
	cd apps/api && DATABASE_URL=sqlite:////tmp/benome_migrate_smoke.sqlite PYTHONPATH=src alembic upgrade head
	rm -f /tmp/benome_migrate_smoke.sqlite

# CI gate
ci: check migrate-smoke

# Apply DB migrations to latest revision
db-upgrade:
	cd apps/api && PYTHONPATH=src alembic upgrade head

# Create a new migration (usage: make db-revision m="add_column")
db-revision:
	cd apps/api && PYTHONPATH=src alembic revision --autogenerate -m "$(m)"

# Show current DB migration revision
db-current:
	cd apps/api && PYTHONPATH=src alembic current
