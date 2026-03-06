from __future__ import annotations

import importlib
from pathlib import Path

from fastapi.testclient import TestClient


def _load_app(tmp_path: Path):
    import benfer_api.core.config as config_module

    config_module.get_settings.cache_clear()
    settings = config_module.get_settings()
    settings.DATABASE_URL = f"sqlite:///{tmp_path / 'benfer-test.sqlite'}"
    settings.CLIPBOARD_STORAGE_PATH = str((tmp_path / "clipboard").resolve())
    settings.ensure_runtime_dirs()

    import benfer_api.main as main_module

    main_module = importlib.reload(main_module)
    return main_module.app, config_module


def test_health(tmp_path: Path):
    app, config_module = _load_app(tmp_path)
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    config_module.get_settings.cache_clear()

