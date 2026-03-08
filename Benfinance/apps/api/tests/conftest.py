
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

API_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(API_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(API_SRC_DIR))


def _run_migrations(database_url: str) -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


@pytest.fixture()
def client(tmp_path: Path):
    db_path = tmp_path / "Benfinance-test.sqlite"
    source_db = Path(__file__).resolve().parents[4] / "database" / "finance.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["SOURCE_DATABASE_PATH"] = str(source_db)
    os.environ["APP_ENV"] = "test"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["SSO_SECRET"] = "test-sso-secret"

    import benfinance_api.core.config as config_module

    config_module.get_settings.cache_clear()
    _run_migrations(os.environ["DATABASE_URL"])

    import benfinance_api.db.session as session_module

    session_module = importlib.reload(session_module)

    import benfinance_api.main as main_module

    main_module = importlib.reload(main_module)

    with TestClient(main_module.create_app()) as test_client:
        yield test_client

    config_module.get_settings.cache_clear()
