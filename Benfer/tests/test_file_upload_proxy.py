from __future__ import annotations

import importlib
from pathlib import Path

from fastapi.testclient import TestClient


def _load_app(tmp_path: Path):
    import benfer_api.core.config as config_module

    config_module.get_settings.cache_clear()
    settings = config_module.get_settings()
    settings.DATABASE_URL = f"sqlite:///{tmp_path / 'benfer-upload-test.sqlite'}"
    settings.CLIPBOARD_STORAGE_PATH = str((tmp_path / "clipboard").resolve())
    settings.ensure_runtime_dirs()

    import benfer_api.main as main_module
    import benfer_api.db.database as database_module
    import benfer_api.api.routes.files as files_module
    import benfer_api.models.file as models_file_module

    database_module = importlib.reload(database_module)
    models_file_module = importlib.reload(models_file_module)
    files_module = importlib.reload(files_module)
    main_module = importlib.reload(main_module)
    database_module.Base.metadata.create_all(bind=database_module.engine)
    return main_module.app, config_module, files_module


def test_single_part_upload_uses_proxy_url_and_accepts_legacy_put(tmp_path: Path, monkeypatch) -> None:
    app, config_module, files_module = _load_app(tmp_path)

    class FakeOSSService:
        def __init__(self) -> None:
            self.objects: dict[str, bytes] = {}

        def generate_oss_key(self, filename: str, user_id: str | None = None) -> str:
            suffix = f"/{user_id}" if user_id else ""
            return f"fake{suffix}/{filename}"

        def upload_file(self, oss_key: str, file_content, content_type: str | None = None) -> bool:
            if hasattr(file_content, "read"):
                payload = file_content.read()
            else:
                payload = file_content
            self.objects[oss_key] = bytes(payload)
            return True

        def file_exists(self, oss_key: str) -> bool:
            return oss_key in self.objects

        def get_download_url(self, oss_key: str, expires_in: int | None = None) -> str:
            return f"https://download.example/{oss_key}"

    fake_oss = FakeOSSService()
    monkeypatch.setattr(files_module, "get_oss_service", lambda: fake_oss)

    from benfer_api.utils.auth import create_session_token

    session_token, _ = create_session_token("benbenbuben", "admin")
    headers = {"Authorization": f"Bearer {session_token}"}

    with TestClient(app) as client:
        init_response = client.post(
            "/api/files/init",
            headers=headers,
            json={
                "filename": "demo.txt",
                "file_size": 5,
                "content_type": "text/plain",
                "chunk_count": 1,
                "is_public": False,
                "expires_in_hours": 24,
            },
        )

        assert init_response.status_code == 200
        init_data = init_response.json()
        assert init_data["chunk_upload_urls"] == [
            f"/api/files/{init_data['upload_id']}/content?upload_token={init_data['access_token']}"
        ]

        put_response = client.put(
            init_data["chunk_upload_urls"][0],
            content=b"hello",
            headers={"Content-Type": "text/plain"},
        )
        assert put_response.status_code == 200
        assert put_response.json()["upload_status"] == "completed"

        complete_response = client.post(f"/api/files/{init_data['upload_id']}/complete", headers=headers)
        assert complete_response.status_code == 200
        assert complete_response.json()["upload_status"] == "completed"
        assert fake_oss.objects["fake/benbenbuben/demo.txt"] == b"hello"

    config_module.get_settings.cache_clear()


def test_download_redirect_and_public_share_routes(tmp_path: Path, monkeypatch) -> None:
    app, config_module, files_module = _load_app(tmp_path)

    class FakeOSSService:
        def __init__(self) -> None:
            self.objects: dict[str, bytes] = {}

        def generate_oss_key(self, filename: str, user_id: str | None = None) -> str:
            suffix = f"/{user_id}" if user_id else ""
            return f"fake{suffix}/{filename}"

        def upload_file(self, oss_key: str, file_content, content_type: str | None = None) -> bool:
            if hasattr(file_content, "read"):
                payload = file_content.read()
            else:
                payload = file_content
            self.objects[oss_key] = bytes(payload)
            return True

        def file_exists(self, oss_key: str) -> bool:
            return oss_key in self.objects

        def get_download_url(self, oss_key: str, expires_in: int | None = None) -> str:
            return f"https://download.example/{oss_key}"

    fake_oss = FakeOSSService()
    monkeypatch.setattr(files_module, "get_oss_service", lambda: fake_oss)

    from benfer_api.utils.auth import create_session_token

    session_token, _ = create_session_token("benbenbuben", "admin")
    headers = {"Authorization": f"Bearer {session_token}"}

    with TestClient(app) as client:
        init_response = client.post(
            "/api/files/init",
            headers=headers,
            json={
                "filename": "public-demo.txt",
                "file_size": 5,
                "content_type": "text/plain",
                "chunk_count": 1,
                "is_public": True,
                "expires_in_hours": 24,
            },
        )

        assert init_response.status_code == 200
        init_data = init_response.json()

        upload_response = client.put(
            init_data["chunk_upload_urls"][0],
            content=b"hello",
            headers={"Content-Type": "text/plain"},
        )
        assert upload_response.status_code == 200

        info_response = client.get(f"/api/files/{init_data['access_token']}", headers=headers)
        assert info_response.status_code == 200
        assert info_response.json()["is_public"] is True

        json_download_response = client.get(f"/api/files/{init_data['access_token']}/download", headers=headers)
        assert json_download_response.status_code == 200
        assert json_download_response.json()["stable_download_url"] == (
            f"/api/files/{init_data['access_token']}/download/redirect"
        )
        assert json_download_response.json()["public_download_url"] == (
            f"/api/files/public/{init_data['access_token']}/download"
        )

        redirect_response = client.get(
            f"/api/files/{init_data['access_token']}/download/redirect",
            headers=headers,
            follow_redirects=False,
        )
        assert redirect_response.status_code == 307
        assert redirect_response.headers["location"] == "https://download.example/fake/benbenbuben/public-demo.txt"

        public_redirect_response = client.get(
            f"/api/files/public/{init_data['access_token']}/download",
            follow_redirects=False,
        )
        assert public_redirect_response.status_code == 307
        assert public_redirect_response.headers["location"] == "https://download.example/fake/benbenbuben/public-demo.txt"

    config_module.get_settings.cache_clear()


def test_public_download_route_rejects_private_files(tmp_path: Path, monkeypatch) -> None:
    app, config_module, files_module = _load_app(tmp_path)

    class FakeOSSService:
        def __init__(self) -> None:
            self.objects: dict[str, bytes] = {}

        def generate_oss_key(self, filename: str, user_id: str | None = None) -> str:
            suffix = f"/{user_id}" if user_id else ""
            return f"fake{suffix}/{filename}"

        def upload_file(self, oss_key: str, file_content, content_type: str | None = None) -> bool:
            if hasattr(file_content, "read"):
                payload = file_content.read()
            else:
                payload = file_content
            self.objects[oss_key] = bytes(payload)
            return True

        def file_exists(self, oss_key: str) -> bool:
            return oss_key in self.objects

        def get_download_url(self, oss_key: str, expires_in: int | None = None) -> str:
            return f"https://download.example/{oss_key}"

    fake_oss = FakeOSSService()
    monkeypatch.setattr(files_module, "get_oss_service", lambda: fake_oss)

    from benfer_api.utils.auth import create_session_token

    session_token, _ = create_session_token("benbenbuben", "admin")
    headers = {"Authorization": f"Bearer {session_token}"}

    with TestClient(app) as client:
        init_response = client.post(
            "/api/files/init",
            headers=headers,
            json={
                "filename": "private-demo.txt",
                "file_size": 5,
                "content_type": "text/plain",
                "chunk_count": 1,
                "is_public": False,
                "expires_in_hours": 24,
            },
        )

        assert init_response.status_code == 200
        init_data = init_response.json()

        upload_response = client.put(
            init_data["chunk_upload_urls"][0],
            content=b"hello",
            headers={"Content-Type": "text/plain"},
        )
        assert upload_response.status_code == 200

        public_redirect_response = client.get(
            f"/api/files/public/{init_data['access_token']}/download",
            follow_redirects=False,
        )
        assert public_redirect_response.status_code == 404

    config_module.get_settings.cache_clear()
