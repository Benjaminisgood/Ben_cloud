from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path):
    db_path = tmp_path / "benusy-test.sqlite"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["DB_BOOTSTRAP_CREATE_ALL"] = "1"
    os.environ["METRICS_UPDATE_INTERVAL_SECONDS"] = "0"
    os.environ["APP_ENV"] = "test"
    os.environ["SSO_SECRET"] = "test-sso-secret"

    import benusy_api.core.config as config_module

    config_module.get_settings.cache_clear()

    import benusy_api.db.database as db_module

    db_module = importlib.reload(db_module)

    import benusy_api.main as main_module

    main_module = importlib.reload(main_module)

    with TestClient(main_module.create_app()) as test_client:
        yield test_client

    config_module.get_settings.cache_clear()
