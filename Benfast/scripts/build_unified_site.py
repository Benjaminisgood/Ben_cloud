#!/usr/bin/env python3
from __future__ import annotations

import json

from services.labdocs_service import labdocs_service


def main() -> None:
    result = labdocs_service.rebuild_site()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
