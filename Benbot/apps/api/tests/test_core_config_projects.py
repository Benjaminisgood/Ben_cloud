from __future__ import annotations

from benbot_api.core.config import Settings


def test_personal_domain_sites_are_registered() -> None:
    settings = Settings(_env_file=None)

    ids = {project.id for project in settings.get_projects()}

    assert {"benprefs", "benhealth", "benfinance", "benself", "benreel", "benvinyl", "bencred", "benlink"} <= ids
