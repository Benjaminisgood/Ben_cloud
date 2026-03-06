from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apps.main import app  # noqa: E402

__all__ = ["app"]


def run() -> None:
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8300"))
    reload_enabled = os.getenv("APP_ENV", "").lower() == "development"
    uvicorn.run("apps.main:app", host=host, port=port, reload=reload_enabled)


if __name__ == "__main__":
    run()
