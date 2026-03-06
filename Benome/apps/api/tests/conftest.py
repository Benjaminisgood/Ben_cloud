from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient


def _upgrade_test_db(database_url: str) -> None:
    api_root = Path(__file__).resolve().parents[1]
    alembic_ini = api_root / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini))
    alembic_cfg.set_main_option("script_location", str(api_root / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_cfg, "head")


@pytest.fixture()
def client(tmp_path: Path):
    db_path = tmp_path / "benome-test.sqlite"
    database_url = f"sqlite:///{db_path}"
    os.environ["DATABASE_URL"] = database_url
    os.environ["DB_BOOTSTRAP_CREATE_ALL"] = "0"
    os.environ["APP_ENV"] = "test"
    os.environ["ADMIN_USERNAME"] = "admin"
    os.environ["ADMIN_PASSWORD"] = "linghome123"

    import benome_api.core.config as config_module

    config_module.get_settings.cache_clear()
    _upgrade_test_db(database_url)

    import benome_api.db.session as db_module

    db_module = importlib.reload(db_module)

    import benome_api.main as main_module

    main_module = importlib.reload(main_module)

    with TestClient(main_module.create_app()) as test_client:
        yield test_client

    config_module.get_settings.cache_clear()
