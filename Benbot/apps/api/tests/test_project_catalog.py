from __future__ import annotations

from benbot_api.core.config import Settings


def test_project_catalog_includes_benjournal() -> None:
    settings = Settings()
    projects = {project.id: project for project in settings.get_projects()}

    assert "benjournal" in projects
    assert projects["benjournal"].port == 9200


def test_project_catalog_includes_benphoto() -> None:
    settings = Settings()
    projects = {project.id: project for project in settings.get_projects()}

    assert "benphoto" in projects
    assert projects["benphoto"].port == 9300


def test_project_catalog_includes_benreel() -> None:
    settings = Settings()
    projects = {project.id: project for project in settings.get_projects()}

    assert "benreel" in projects
    assert projects["benreel"].port == 9500


def test_project_catalog_includes_benvinyl() -> None:
    settings = Settings()
    projects = {project.id: project for project in settings.get_projects()}

    assert "benvinyl" in projects
    assert projects["benvinyl"].port == 9400


def test_project_catalog_includes_bencred() -> None:
    settings = Settings()
    projects = {project.id: project for project in settings.get_projects()}

    assert "bencred" in projects
    assert projects["bencred"].port == 9600
    assert projects["bencred"].sso_enabled is False
    assert projects["bencred"].sso_entry_path == "/"


def test_project_catalog_includes_benlink() -> None:
    settings = Settings()
    projects = {project.id: project for project in settings.get_projects()}

    assert "benlink" in projects
    assert projects["benlink"].port == 9700
    assert projects["benlink"].sso_enabled is False
    assert projects["benlink"].sso_entry_path == "/"


def test_project_catalog_includes_benself() -> None:
    settings = Settings()
    projects = {project.id: project for project in settings.get_projects()}

    assert "benself" in projects
    assert projects["benself"].port == 9800
    assert projects["benself"].sso_enabled is True
