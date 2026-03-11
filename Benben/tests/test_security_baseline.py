from __future__ import annotations

import base64
import hashlib
import hmac
import importlib
import json
from pathlib import Path
import sys
import time
from datetime import date

import pytest
from fastapi.testclient import TestClient


def _current_week_folder() -> str:
    iso = date.today().isocalendar()
    return f"writing/{iso.year}-W{iso.week:02d}"


def _load_app_module(monkeypatch: pytest.MonkeyPatch, *, audit_log_path: str | None = None):
    monkeypatch.setenv("BENBEN_OSS_ENDPOINT", "oss-cn-shanghai.aliyuncs.com")
    monkeypatch.setenv("BENBEN_OSS_ACCESS_KEY_ID", "dummy")
    monkeypatch.setenv("BENBEN_OSS_ACCESS_KEY_SECRET", "dummy")
    monkeypatch.setenv("BENBEN_OSS_BUCKET_NAME", "dummy")
    monkeypatch.setenv("BENBEN_OSS_PREFIX", "benben")
    monkeypatch.setenv("BENBEN_SSO_SECRET", "dummy")
    monkeypatch.setenv("BENBEN_SESSION_SECRET_KEY", "dummy-session-secret")
    monkeypatch.setenv("BENBEN_UPLOAD_MAX_BYTES", "1024")
    monkeypatch.setenv("BENBEN_UPLOAD_MAX_REQUESTS_PER_MINUTE", "10")
    monkeypatch.setenv("BENBEN_MARKDOWN_MAX_BYTES", "1024")
    if audit_log_path:
        monkeypatch.setenv("BENBEN_AUDIT_LOG_PATH", audit_log_path)
        monkeypatch.setenv("BENBEN_AUDIT_MAX_BYTES", "2048")

    for name in list(sys.modules):
        if name == "app" or name.startswith("apps") or name.startswith("benben_api"):
            sys.modules.pop(name, None)

    module = importlib.import_module("app")
    return module


class _FakeOSS:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def list_markdown_files(self) -> list[str]:
        return sorted(self.store.keys())

    def read_file(self, rel_path: str):
        if rel_path not in self.store:
            from apps.services.storage import FileNotFoundErrorInStore

            raise FileNotFoundErrorInStore(rel_path)
        from apps.services.storage import FileSnapshot

        content = self.store[rel_path]
        version = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return FileSnapshot(path=rel_path, content=content, version=version)

    def normalize_markdown_path(self, path: str) -> str:
        from apps.services.storage import OSSRepository

        return OSSRepository.normalize_markdown_path(self, path)  # type: ignore[misc]

    def save_file(self, rel_path: str, content: str, *, base_version: str | None, force: bool):
        from apps.services.storage import SaveResult, VersionConflictError

        created = rel_path not in self.store
        if not created:
            current = self.store[rel_path]
            current_version = hashlib.sha256(current.encode("utf-8")).hexdigest()
            if not force and base_version != current_version:
                raise VersionConflictError(
                    path=rel_path,
                    current_version=current_version,
                    current_content=current,
                )

        self.store[rel_path] = content
        version = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return SaveResult(path=rel_path, version=version, created=created)

    def delete_file(self, rel_path: str) -> None:
        self.store.pop(rel_path, None)

    def upload_image(self, _file):
        return "https://example.com/uploaded.png"


def _build_sso_token(secret: str, *, username: str = "ben", role: str = "admin") -> str:
    payload = {
        "u": username,
        "r": role,
        "e": int(time.time()) + 30,
        "n": "abcdef12",
    }
    data = json.dumps(payload, separators=(",", ":"))
    signature = hmac.new(secret.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).hexdigest()
    raw = f"{data}.{signature}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8").rstrip("=")


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    audit_log_path = tmp_path / "benben_audit.log"
    _load_app_module(monkeypatch, audit_log_path=str(audit_log_path))

    from apps.main import app
    from apps.services.storage import get_repository

    fake_repo = _FakeOSS()
    app.dependency_overrides[get_repository] = lambda: fake_repo

    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def _read_audit_records(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_auth_required_for_api(client: TestClient) -> None:
    unauthorized = client.get("/api/files")
    assert unauthorized.status_code == 401


def test_health_endpoints_and_request_id(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.headers.get("x-request-id")
    assert health.headers.get("x-process-time-ms")

    live = client.get("/health/live")
    assert live.status_code == 200
    assert live.json()["status"] == "live"

    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    assert ready.json()["checks"]["audit_log_dir_writable"] is True


def test_sso_login_and_versioned_save_flow(client: TestClient) -> None:
    token = _build_sso_token("dummy")
    login = client.get(f"/auth/sso?token={token}", follow_redirects=False)
    assert login.status_code == 302

    first_save = client.post(
        "/api/files",
        json={"path": "report.md", "content": "# v1", "base_version": None},
    )
    assert first_save.status_code == 200
    assert first_save.json()["operation_id"]
    first_version = first_save.json()["version"]

    second_save = client.post(
        "/api/files",
        json={"path": "report.md", "content": "# v2", "base_version": first_version},
    )
    assert second_save.status_code == 200

    conflict = client.post(
        "/api/files",
        json={"path": "report.md", "content": "# stale", "base_version": first_version},
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["detail"] == "version_conflict"

    session = client.get("/api/session")
    assert session.status_code == 200
    request_id = session.headers.get("x-request-id")
    assert request_id


def test_editor_home_page_contains_workspace_and_slide_support(client: TestClient) -> None:
    token = _build_sso_token("dummy", username="designer")
    login = client.get(f"/auth/sso?token={token}", follow_redirects=False)
    assert login.status_code == 302

    page = client.get("/")
    assert page.status_code == 200
    assert "模版" in page.text
    assert "写作" in page.text
    assert "文档" in page.text
    assert "幻灯片" in page.text
    assert "导出" in page.text
    assert "slash-panel" in page.text
    assert "Markdown + Slides" in page.text
    assert "/static/editor.css" in page.text
    assert "/static/editor.js" in page.text


def test_storage_config_error_returns_503_with_clear_detail(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    audit_log_path = tmp_path / "benben_audit.log"
    _load_app_module(monkeypatch, audit_log_path=str(audit_log_path))
    monkeypatch.setenv("BENBEN_OSS_BUCKET_NAME", "your_bucket_name")

    for name in list(sys.modules):
        if name == "app" or name.startswith("apps") or name.startswith("benben_api"):
            sys.modules.pop(name, None)

    importlib.import_module("app")
    from apps.main import app

    raw_client = TestClient(app)
    token = _build_sso_token("dummy", username="designer")
    login = raw_client.get(f"/auth/sso?token={token}", follow_redirects=False)
    assert login.status_code == 302

    listed = raw_client.get("/api/files")
    assert listed.status_code == 503
    assert "BENBEN_OSS_BUCKET_NAME" in listed.json()["detail"]


def test_templates_endpoint_and_creation(client: TestClient) -> None:
    token = _build_sso_token("dummy", username="alice")
    client.get(f"/auth/sso?token={token}", follow_redirects=False)

    templates = client.get("/api/templates")
    assert templates.status_code == 200
    ids = {item["id"] for item in templates.json()["templates"]}
    assert "weekly_report" in ids

    created = client.post(
        "/api/files/from-template",
        json={
            "path": "alice-weekly.md",
            "template_id": "weekly_report",
            "project": "Benlab",
        },
    )
    assert created.status_code == 200
    assert created.json()["template_id"] == "weekly_report"
    assert created.json()["operation_id"]
    created_path = created.json()["path"]
    assert created_path.startswith(f"{_current_week_folder()}/")

    loaded = client.get(f"/api/files/{created_path}")
    assert loaded.status_code == 200
    assert "Benlab" in loaded.json()["content"]
    assert "alice" in loaded.json()["content"].lower()


def test_write_and_template_scopes_are_isolated(client: TestClient) -> None:
    token = _build_sso_token("dummy", username="scope-user")
    client.get(f"/auth/sso?token={token}", follow_redirects=False)

    template_saved = client.post(
        "/api/template-files",
        json={"path": "templates/base.md", "content": "# base", "base_version": None},
    )
    assert template_saved.status_code == 200

    write_saved = client.post(
        "/api/files",
        json={"path": "todo.md", "content": "# this week", "base_version": None},
    )
    assert write_saved.status_code == 200
    write_path = write_saved.json()["path"]
    assert write_path.startswith(f"{_current_week_folder()}/")

    listed = client.get("/api/files")
    assert listed.status_code == 200
    files = listed.json()["files"]
    assert write_path in files
    assert "templates/base.md" not in files

    reject_template_from_write_api = client.get("/api/files/templates/base.md")
    assert reject_template_from_write_api.status_code == 400


def test_export_api_supports_txt_md_html(client: TestClient, tmp_path: Path) -> None:
    token = _build_sso_token("dummy", username="exporter")
    login = client.get(f"/auth/sso?token={token}", follow_redirects=False)
    assert login.status_code == 302

    payload = {
        "content": "# 周报标题\n\n- 进展 A\n- 进展 B\n",
        "file_name": "weekly/2026w10.md",
    }

    txt_res = client.post("/api/export", json={"format": "txt", **payload})
    assert txt_res.status_code == 200
    assert txt_res.headers["content-type"].startswith("text/plain")
    assert 'filename="2026w10.txt"' in txt_res.headers.get("content-disposition", "")
    export_op_id = txt_res.headers.get("x-operation-id")
    assert export_op_id
    assert "周报标题" in txt_res.text

    md_res = client.post("/api/export", json={"format": "md", **payload})
    assert md_res.status_code == 200
    assert md_res.headers["content-type"].startswith("text/markdown")
    assert md_res.text == payload["content"]

    html_res = client.post("/api/export", json={"format": "html", **payload})
    assert html_res.status_code == 200
    assert html_res.headers["content-type"].startswith("text/html")
    assert "<html" in html_res.text.lower()
    assert "周报标题" in html_res.text

    audit_log_path = tmp_path / "benben_audit.log"
    records = _read_audit_records(audit_log_path)
    matched = [item for item in records if item.get("action") == "export_note" and item.get("operation_id") == export_op_id]
    assert matched, "export_note 审计日志中缺少 operation_id 关联记录"


def test_write_operation_id_is_recorded_in_audit_log(
    client: TestClient,
    tmp_path: Path,
) -> None:
    token = _build_sso_token("dummy", username="auditor")
    login = client.get(f"/auth/sso?token={token}", follow_redirects=False)
    assert login.status_code == 302

    saved = client.post(
        "/api/files",
        json={"path": "audit/report.md", "content": "# audit", "base_version": None},
    )
    assert saved.status_code == 200
    op_id = saved.json()["operation_id"]

    audit_log_path = tmp_path / "benben_audit.log"
    records = _read_audit_records(audit_log_path)
    matched = [item for item in records if item.get("action") == "save_file" and item.get("operation_id") == op_id]
    assert matched, "save_file 审计日志中缺少 operation_id 关联记录"
