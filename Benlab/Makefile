.PHONY: install dev test check migrate-smoke ci db-upgrade db-revision db-current automation-openapi automation-smoke

PYTEST_DISABLE_PLUGIN_AUTOLOAD ?= 1

# Install the FastAPI backend (standardized package)
install:
	cd apps/api && python3 -m pip install -e ".[dev]"

# Start the standardized FastAPI entrypoint
dev:
	cd apps/api && PYTHONPATH=src uvicorn benlab_api.main:app --app-dir src --reload --host 0.0.0.0 --port 9000

# Run backend tests
test:
	cd apps/api && PYTEST_DISABLE_PLUGIN_AUTOLOAD=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD) PYTHONPATH=src pytest -q

# Run unified backend quality gate
check:
	cd apps/api && PYTHONPATH=src python -m compileall -q src/benlab_api
	cd apps/api && PYTEST_DISABLE_PLUGIN_AUTOLOAD=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD) PYTHONPATH=src pytest -q
	cd apps/api && PYTHONPATH=src alembic current

# Run migration smoke test on temporary SQLite DB
migrate-smoke:
	cd apps/api && DATABASE_URL=sqlite:////tmp/benlab_migrate_smoke.sqlite PYTHONPATH=src alembic upgrade head
	rm -f /tmp/benlab_migrate_smoke.sqlite

# CI gate (same as workflow)
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

# Export OpenAPI schema for external automation tools
automation-openapi:
	PYTHONPATH=apps/api/src python3 -c 'import json, pathlib; from benlab_api.main import app; out = pathlib.Path("automation/openapi.json"); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); print(out)'

# Run end-to-end automation smoke test against a running Benlab API
automation-smoke:
	bash scripts/automation_smoke.sh
