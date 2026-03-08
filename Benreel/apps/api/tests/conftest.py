from __future__ import annotations

import importlib
import json
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
    db_path = tmp_path / "benreel-test.sqlite"
    manifest_path = tmp_path / "video_library.json"
    manifest_path.write_text(
        json.dumps(
            {
                "videos": [
                    {
                        "id": "midnight-train",
                        "title": "午夜列车",
                        "url": "https://oss-example.oss-cn-shanghai.aliyuncs.com/videos/midnight-train.mp4",
                        "poster_url": "https://oss-example.oss-cn-shanghai.aliyuncs.com/posters/midnight-train.jpg",
                        "summary": "夜色和窗外灯带交替掠过。",
                        "duration_label": "02:14",
                    },
                    {
                        "id": "harbor-dog",
                        "title": "港口小狗",
                        "url": "https://oss-example.oss-cn-shanghai.aliyuncs.com/videos/harbor-dog.mp4",
                        "poster_url": "https://oss-example.oss-cn-shanghai.aliyuncs.com/posters/harbor-dog.jpg",
                        "summary": "一只狗在清晨码头追着风跑。",
                        "duration_label": "01:06",
                    },
                    {
                        "id": "late-sun",
                        "title": "傍晚余照",
                        "url": "https://oss-example.oss-cn-shanghai.aliyuncs.com/videos/late-sun.mp4",
                        "poster_url": "https://oss-example.oss-cn-shanghai.aliyuncs.com/posters/late-sun.jpg",
                        "summary": "太阳快落山时的橘色地平线。",
                        "duration_label": "03:02",
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["VIDEO_LIBRARY_PATH"] = str(manifest_path)
    os.environ["DAILY_VIDEO_COUNT"] = "2"
    os.environ["APP_ENV"] = "test"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["SSO_SECRET"] = "test-sso-secret"

    import benreel_api.core.config as config_module

    config_module.get_settings.cache_clear()
    _run_migrations(os.environ["DATABASE_URL"])

    import benreel_api.db.session as session_module

    importlib.reload(session_module)

    import benreel_api.main as main_module

    main_module = importlib.reload(main_module)

    with TestClient(main_module.create_app()) as test_client:
        yield test_client

    config_module.get_settings.cache_clear()
