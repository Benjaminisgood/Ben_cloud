from __future__ import annotations

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
API_SRC = ROOT_DIR / "apps" / "api" / "src"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

from benfer_api.main import run  # noqa: E402


if __name__ == "__main__":
    run()
