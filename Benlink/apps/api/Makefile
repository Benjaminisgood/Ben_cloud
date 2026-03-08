.PHONY: install dev run test migrate clean

PYTEST_DISABLE_PLUGIN_AUTOLOAD ?= 1

# Install dependencies
install:
	pip install -e ".[dev]"

# Development install with hot reload
dev:
	DEBUG=true uvicorn benlink_api.main:app --reload --host 0.0.0.0 --port 9700

# Run in production mode
run:
	uvicorn benlink_api.main:app --host 0.0.0.0 --port 9700

# Run tests
test:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD) PYTHONPATH=src pytest -p pytest_asyncio.plugin tests/ -v

# Create Alembic migration
migrate-gen:
	PYTHONPATH=src alembic revision --autogenerate -m "$(m)"

# Run Alembic migrations
migrate:
	PYTHONPATH=src alembic upgrade head

# Rollback last migration
migrate-down:
	PYTHONPATH=src alembic downgrade -1

# Show migration history
migrate-history:
	PYTHONPATH=src alembic history

# Clean build artifacts
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -name "*.pyc" -delete
